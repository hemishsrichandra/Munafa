"""Evidence-linked read model. No prediction or generated merchant facts."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from fastapi import APIRouter
from . import auth, store, models as m, inventory, payments
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
    for c in store.all_cases(db):
        c = present(c)
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
        "receivables_available": False,
    }


@router.get("/brief")
def brief():
    with store.connect() as db:
        return build(db)
