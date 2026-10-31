"""Evidence-linked read model. No prediction or generated merchant facts."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from fastapi import APIRouter
from . import auth, store, models as m, inventory, payments, records
from .domain import local_today, present

router = APIRouter(prefix="/api")


def build(db):
    p = auth.current()
    now, today = datetime.now(timezone.utc), local_today()
    mode = "demo" if p.demo else "live"
    payment = payments.overview(db, mode)
    items = []

    def add(
        kind, eid, title, reason, priority, source_ids, route, observed, status="open", demo=None
    ):
        observed = observed if isinstance(observed, datetime) else datetime.fromisoformat(observed)
        items.append(
            {
                "action_id": f"{kind}:{eid}",
                "type": kind,
                "priority": priority,
                "title": title,
                "reason": reason,
                "source_entity_ids": source_ids,
                "data_freshness": {
                    "source_updated_at": observed,
                    "queried_at": now,
                    "stale": now - observed > timedelta(hours=24),
                },
                "status": status,
                "route": route,
                "mode": mode if demo is None else demo,
            }
        )

    for r in payment["settlements"]:
        if r["needs_review"]:
            add(
                "reconciliation",
                r["batch_id"],
                "Review settlement components",
                "; ".join(
                    x["detail"] for x in r["reasons"] if x["classification"] == "review_candidate"
                ),
                1,
                r["source_entity_ids"],
                f"/payments/{r['batch_id']}?mode={mode}",
                r["observed_at"],
            )
    cases = [present(c) for c in store.all_cases(db)]
    onboarding = None
    for c in cases:
        if c["status"] == "review":
            add(
                "invoice_review",
                c["id"],
                "Review invoice " + c["invoice"]["reference"],
                "Confirm the bill and count the physical delivery separately. Nothing has been approved or recovered.",
                2,
                [c["id"]],
                f"/cases/{c['id']}",
                c["created_at"],
            )
        if p.demo and c["synthetic"] and c["invoice"]["reference"] == "A-104":
            approved = c["approved_version"] is not None
            shared = c["status"] in ("sent", "promised", "partial", "resolved")
            onboarding = {
                "source_entity_ids": [c["id"]],
                "route": f"/cases/{c['id']}",
                "title": "Continue your sample invoice"
                if c["status"] != "resolved"
                else "Review your completed sample",
                "next_step": "Review the bill and confirm what actually arrived."
                if c["status"] == "review"
                else "Approve the reviewed evidence."
                if not approved
                else "Review the sharing handoff; no message is sent automatically."
                if not shared
                else "Record a supplier promise only when received, then confirm recovery with proof."
                if c["status"] != "resolved"
                else "Your sample has proof-backed recovery. You can inspect its history.",
                "steps": [
                    {"label": "Confirm quantities and units", "complete": c["status"] != "review"},
                    {"label": "Approve the evidence", "complete": approved},
                    {"label": "Review sharing handoff", "complete": shared},
                    {"label": "Confirm recovery with proof", "complete": c["status"] == "resolved"},
                ],
                "synthetic": True,
            }

        if c["status"] in ("ready", "sent", "promised", "partial") and c["remaining_paise"] > 0:
            overdue = bool(c["follow_up"] and c["follow_up"] < today.isoformat())
            latest = (
                db.execute(
                    select(func.max(m.audit_events.c.at)).where(
                        store.scope(m.audit_events), m.audit_events.c.entity_id == c["id"]
                    )
                ).scalar()
                or c["created_at"]
            )
            add(
                "supplier_followup",
                c["id"],
                f"Follow up: {c['invoice']['supplier']}",
                "Recorded supplier promise is overdue; recovery is unverified."
                if overdue
                else "An approved supplier claim remains open. A promise is not recovered money.",
                1 if overdue else 3,
                [c["id"]],
                f"/cases/{c['id']}",
                latest,
                c["status"],
            )
    for product in inventory.products(db):
        if product["below_threshold"]:
            latest = (
                db.execute(
                    select(func.max(m.inventory_events.c.at)).where(
                        store.scope(m.inventory_events),
                        m.inventory_events.c.product_id == product["id"],
                    )
                ).scalar()
                or product["created_at"]
            )
            add(
                "low_stock",
                product["id"],
                f"Check stock: {product['name']}",
                f"Recorded stock {product['stock_quantity']} {product['unit']} is at/below your {product['reorder_threshold']} {product['unit']} threshold. No order has been placed.",
                3,
                [product["id"]],
                f"/stock/{product['id']}",
                latest,
            )
        for lot in inventory.lots(db, product["id"]):
            if (
                lot["expiry_date"]
                and lot["quantity"] != "0"
                and lot["expiry_date"] <= (today + timedelta(days=30)).isoformat()
            ):
                add(
                    "expiry",
                    lot["id"],
                    f"Check expiry: {product['name']}",
                    f"Recorded batch expiry: {lot['expiry_date']}; verify physical stock.",
                    2,
                    [product["id"], lot["id"]],
                    f"/stock/{product['id']}",
                    product["created_at"],
                )
    # Accepted manual records only: collections are not another sale; reversals cancel originals.
    history = records.all_entries(db)
    active = records.active_entries(db, history)
    sales = [r for r in active if r["kind"] in ("cash_sale", "credit_sale")]
    expenses = [r for r in active if r["kind"] == "expense"]
    obligations = [r for r in active if r["kind"] in ("opening_due", "credit_sale")]
    dues = [(r, records.outstanding(active, r)) for r in obligations]
    for r, remaining in dues:
        if remaining > 0 and r["due_on"] and r["due_on"] <= today:
            add(
                "customer_due",
                r["id"],
                "Review customer payment due",
                f"{remaining // 100}.{remaining % 100:02d} INR remains on your recorded obligation, due {r['due_on']}. No bank receipt or reminder delivery is verified.",
                1 if r["due_on"] < today else 2,
                [r["id"], r["customer_id"]],
                f"/records/entries/{r['id']}",
                r["created_at"],
            )
    tasks = [
        dict(t)
        for t in db.execute(
            select(m.business_tasks).where(store.scope(m.business_tasks))
        ).mappings()
    ]
    open_tasks = [t for t in tasks if t["status"] == "open"]
    for t in open_tasks:
        if p.role != "owner" and t["assignee_id"] not in (None, p.user_id):
            continue
        latest = (
            db.execute(
                select(func.max(m.audit_events.c.at)).where(
                    store.scope(m.audit_events), m.audit_events.c.entity_id == t["id"]
                )
            ).scalar()
            or t["created_at"]
        )
        add(
            "store_task",
            t["id"],
            t["title"],
            f"Recorded {t['category']} task due {t['due_on']}. Open the task before changing its status.",
            2 if t["due_on"] <= today else 4,
            [t["id"]],
            f"/records/tasks/{t['id']}",
            latest,
        )
    totals = {
        "cash": records.build_summary(db, history=history)["cash"],
        "mode": "demo" if p.demo else "manual",
        "source": "merchant_reviewed_manual",
        "coverage": "All recorded dates; not complete shop sales, profit or bank verification.",
        "sales_paise": sum(r["amount_paise"] for r in sales),
        "expenses_paise": sum(r["amount_paise"] for r in expenses),
        "customer_dues_paise": sum(remaining for _, remaining in dues),
        "open_tasks": len(open_tasks),
        "record_count": len(history),
        "queried_at": now,
        "last_source_at": max((r["created_at"] for r in history), default=None),
        "business_date": today,
        "today": {
            "sales_paise": sum(r["amount_paise"] for r in sales if r["occurred_on"] == today),
            "expenses_paise": sum(r["amount_paise"] for r in expenses if r["occurred_on"] == today),
        },
        "source_routes": {
            "sales": "/records/history?group=sales",
            "expenses": "/records/history?group=expenses",
            "dues": "/records/customers",
            "tasks": "/records/tasks",
        },
    }
    # This is recorded collection activity, never SKU sales. Unavailable != zero.
    yesterday = today - timedelta(days=1)
    rows = list(
        db.execute(
            select(m.payment_events).where(
                store.scope(m.payment_events), m.payment_events.c.mode == mode
            )
        ).mappings()
    )
    latest, conflicts = payments.current_events(rows)
    available = bool(rows) and not conflicts
    collections = (
        sum(
            r["amount_paise"]
            for (_, kind), r in latest.items()
            if kind == "payment"
            and r["status"] == "succeeded"
            and r["occurred_at"].astimezone(ZoneInfo(p.timezone)).date() == yesterday
        )
        if available
        else None
    )
    settlements = (
        sum(
            r["recorded_settled_paise"]
            for r in payment["settlements"]
            if r["status"] == "settled"
            and r["payout_at"]
            and r["payout_at"].astimezone(ZoneInfo(p.timezone)).date() == yesterday
            and r["recorded_settled_paise"] is not None
        )
        if payment["settlements"]
        else None
    )
    return {
        "generated_at": now,
        "business_date": today,
        "timezone": p.timezone,
        "mode": mode,
        "payment_label": payment["label"],
        "last_payment_source_at": payment["last_source_at"],
        "yesterday": {
            "date": yesterday,
            "recorded_collections_paise": collections,
            "recorded_settlements_paise": settlements,
            "coverage": "Partial source observations only; not a complete business-day total."
            if rows
            else "Unavailable: no connected payment records.",
        },
        "items": sorted(items, key=lambda x: (x["priority"], x["action_id"]))[:7],
        "omitted_count": max(0, len(items) - 7),
        "receivables_available": True,
        "manual_totals": totals,
        "onboarding": onboarding,
    }


@router.get("/brief")
def brief():
    with store.connect() as db:
        return build(db)
