"""Merchant-reviewed records, separate from provider observations and supplier claims."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter, Query
from pydantic import Field, model_validator
from sqlalchemy import select, insert, update
from . import auth, models as m, store
from .domain import StrictModel, RuleError, normalized

router = APIRouter(prefix="/api/records")
Kind = Literal[
    "opening_due",
    "credit_sale",
    "cash_sale",
    "collection",
    "expense",
    "opening_cash",
    "payable",
    "payable_payment",
]
Category = Literal["stock", "rent", "utilities", "wages", "transport", "other"]


def today():
    return datetime.now(ZoneInfo(auth.current().timezone)).date()


def now():
    return datetime.now(timezone.utc)


def lock(db):
    # Serialises allocation/reversal and consent writes within this store.
    db.execute(
        select(m.stores.c.id).where(m.stores.c.id == auth.current().store_id).with_for_update()
    ).one()


def get(db, table, eid):
    r = db.execute(select(table).where(store.scope(table), table.c.id == eid)).mappings().first()
    if not r:
        raise KeyError(eid)
    return dict(r)


def audit(db, eid, detail, version=None, snapshot=None):
    store.audit_record(
        db, eid, detail, new=version, entity_type="business_record", snapshot=snapshot
    )


class Customer(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    reference: str = Field(min_length=1, max_length=80)
    phone: str = Field(default="", pattern=r"^\+?[0-9]{0,15}$")
    marketing_consent: bool = False
    consent_note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def consent(self):
        if self.marketing_consent and len(self.consent_note) < 3:
            raise ValueError("Record how and when this customer agreed to marketing drafts.")
        return self


class CustomerEdit(Customer):
    version: int = Field(ge=1, strict=True)


class Entry(StrictModel):
    kind: Kind
    customer_id: str | None = Field(default=None, max_length=64)
    reference: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=0, le=1000000000000, strict=True)
    occurred_on: date
    due_on: date | None = None
    category: Category = "other"
    payment_channel: Literal["cash", "bank", "upi", "other"] = "cash"
    note: str = Field(min_length=3, max_length=500)
    target_id: str | None = Field(default=None, max_length=64)
    merchant_confirmed: bool = False


class Reverse(StrictModel):
    reference: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=500)
    merchant_confirmed: bool = False


class Task(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    category: Literal["opening", "closing", "followup", "compliance", "other"] = "other"
    due_on: date
    assignee_id: str | None = Field(default=None, max_length=64)
    note: str = Field(default="", max_length=500)


class TaskStatus(StrictModel):
    version: int = Field(ge=1, strict=True)
    status: Literal["open", "done"]


class Campaign(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=1600)
    recipient_ids: list[str] = Field(min_length=1, max_length=100)
    merchant_confirmed: bool = False


@router.get("/customers")
def customers():
    with store.connect() as db:
        return [
            dict(r)
            for r in db.execute(
                select(m.business_customers)
                .where(store.scope(m.business_customers))
                .order_by(m.business_customers.c.name)
            ).mappings()
        ]


@router.post("/customers", status_code=201)
def create_customer(body: Customer):
    with store.connect("write") as db:
        lock(db)
        eid = store.uid()
        db.execute(
            insert(m.business_customers).values(
                id=eid,
                store_id=auth.current().store_id,
                **body.model_dump(),
                version=1,
                actor_id=auth.current().user_id,
                created_at=now(),
            )
        )
        audit(
            db,
            eid,
            "Customer recorded; consent is limited to local marketing draft selection",
            1,
            snapshot={
                "purpose": "local_marketing_draft_selection",
                "choice": body.marketing_consent,
                "note": body.consent_note,
            },
        )
        return get(db, m.business_customers, eid)


@router.patch("/customers/{eid}")
def edit_customer(eid: str, body: CustomerEdit):
    with store.connect("write") as db:
        lock(db)
        old = get(db, m.business_customers, eid)
        if old["version"] != body.version:
            raise RuleError("Customer changed. Reload before reviewing contact or consent.")
        db.execute(
            update(m.business_customers)
            .where(store.scope(m.business_customers), m.business_customers.c.id == eid)
            .values(**body.model_dump(exclude={"version"}), version=body.version + 1)
        )
        audit(
            db,
            eid,
            "Customer/contact consent reviewed",
            body.version + 1,
            snapshot={
                "purpose": "local_marketing_draft_selection",
                "prior_choice": old["marketing_consent"],
                "choice": body.marketing_consent,
                "note": body.consent_note,
            },
        )
        return get(db, m.business_customers, eid)


def all_entries(db):
    rows = [
        dict(r)
        for r in db.execute(
            select(m.business_entries)
            .where(store.scope(m.business_entries))
            .order_by(m.business_entries.c.created_at, m.business_entries.c.id)
            .limit(10001)
        ).mappings()
    ]
    if sum(r["amount_paise"] for r in rows) > 1000000000000000:
        raise RuleError(
            "Manual ledger exceeds the exact display capacity; no rounded balances are shown."
        )
    if len(rows) > 10000:
        raise RuleError(
            "Manual ledger exceeds this prototype's review limit; no incomplete balance is displayed."
        )
    return rows


def active_entries(db, rows=None):
    rows = all_entries(db) if rows is None else rows
    reversed_ids = {r["reversal_of"] for r in rows if r["kind"] == "reversal"}
    return [r for r in rows if r["kind"] != "reversal" and r["id"] not in reversed_ids]


def outstanding(rows, obligation):
    return obligation["amount_paise"] - sum(
        r["amount_paise"] for r in rows if r["target_id"] == obligation["id"]
    )


@router.post("/entries", status_code=201)
def record_entry(body: Entry):
    with store.connect("write") as db:
        lock(db)
        if not body.merchant_confirmed:
            raise RuleError("Review the amount, source and kind, then confirm this manual record.")
        if body.occurred_on > today():
            raise RuleError(
                "Actual records cannot have a future date; use a payable or task for plans."
            )
        if body.due_on and (
            body.kind not in ("opening_due", "credit_sale", "payable")
            or body.due_on < body.occurred_on
        ):
            raise RuleError("Only obligations have due dates, on or after their record date.")
        if body.customer_id:
            get(db, m.business_customers, body.customer_id)
        if body.kind in ("opening_due", "credit_sale", "collection") and not body.customer_id:
            raise RuleError("Choose the customer whose debt or collection is being recorded.")
        if (
            body.kind in ("expense", "opening_cash", "payable", "payable_payment")
            and body.customer_id
        ):
            raise RuleError("This entry does not belong to a customer debt account.")
        history = all_entries(db)
        if (
            len(history) >= 9990
            or sum(r["amount_paise"] for r in history) + body.amount_paise > 1000000000000000
        ):
            raise RuleError(
                "Manual ledger has reached this prototype's capacity. No entry was posted."
            )
        rows = active_entries(db, history)
        if body.kind in ("collection", "payable_payment"):
            if not body.target_id:
                raise RuleError("Allocate this payment to one explicit open obligation.")
            target = get(db, m.business_entries, body.target_id)
            expected = ("opening_due", "credit_sale") if body.kind == "collection" else ("payable",)
            if (
                target["kind"] not in expected
                or target["customer_id"] != body.customer_id
                or target["id"] not in {r["id"] for r in rows}
            ):
                raise RuleError(
                    "Payment target is reversed, incompatible or belongs to another customer."
                )
            if body.occurred_on < target["occurred_on"] or body.amount_paise > outstanding(
                rows, target
            ):
                raise RuleError(
                    "Payment cannot predate or exceed the remaining obligation. Record partial payments separately."
                )
        elif body.target_id:
            raise RuleError("Only collections and payable payments have allocation targets.")
        if body.kind == "opening_cash" and body.payment_channel != "cash":
            raise RuleError("Opening cash is a cash-drawer balance, not a bank balance.")
        if body.kind == "opening_cash" and any(r["kind"] == "opening_cash" for r in rows):
            raise RuleError(
                "An opening cash balance already exists. Reverse it explicitly before correcting it."
            )
        if body.kind == "opening_cash" and any(
            r["occurred_on"] < body.occurred_on
            and r["payment_channel"] == "cash"
            and r["kind"] in ("cash_sale", "collection", "expense", "payable_payment")
            for r in rows
        ):
            raise RuleError("Opening cash must be on or before all recorded cash movements.")
        opening = next((r for r in rows if r["kind"] == "opening_cash"), None)
        if (
            opening
            and body.payment_channel == "cash"
            and body.kind in ("cash_sale", "collection", "expense", "payable_payment")
            and body.occurred_on < opening["occurred_on"]
        ):
            raise RuleError(
                "Cash movement predates the opening balance. Review the opening record first."
            )
        eid = store.uid()
        db.execute(
            insert(m.business_entries).values(
                id=eid,
                store_id=auth.current().store_id,
                **body.model_dump(exclude={"merchant_confirmed"}),
                reference_key=normalized(body.reference),
                reversal_of=None,
                actor_id=auth.current().user_id,
                created_at=now(),
            )
        )
        audit(db, eid, "Reviewed manual " + body.kind + "; not bank/POS verified")
        return get(db, m.business_entries, eid)


@router.post("/entries/{eid}/reverse", status_code=201)
def reverse_entry(eid: str, body: Reverse):
    with store.connect("approve") as db:
        lock(db)
        old = get(db, m.business_entries, eid)
        history = all_entries(db)
        if (
            len(history) >= 10000
            or sum(r["amount_paise"] for r in history) + old["amount_paise"] > 1000000000000000
        ):
            raise RuleError(
                "Manual ledger correction exceeds this prototype's capacity. No record was changed."
            )
        rows = active_entries(db, history)
        if not body.merchant_confirmed or eid not in {r["id"] for r in rows}:
            raise RuleError("Confirm an active entry before reversing it.")
        if any(r["target_id"] == eid for r in rows):
            raise RuleError(
                "Reverse allocated payments first; debt/payment history cannot be silently rewritten."
            )
        rid = store.uid()
        db.execute(
            insert(m.business_entries).values(
                id=rid,
                store_id=auth.current().store_id,
                customer_id=old["customer_id"],
                kind="reversal",
                reference=body.reference,
                reference_key=normalized(body.reference),
                amount_paise=old["amount_paise"],
                occurred_on=today(),
                due_on=None,
                category=old["category"],
                payment_channel=old["payment_channel"],
                note=body.reason,
                target_id=None,
                reversal_of=eid,
                actor_id=auth.current().user_id,
                created_at=now(),
            )
        )
        audit(db, rid, "Manual entry reversed; original retained: " + eid)
        return get(db, m.business_entries, rid)


def build_summary(db, history=None):
    history = all_entries(db) if history is None else history
    rows = active_entries(db, history)
    people = [
        dict(r)
        for r in db.execute(
            select(m.business_customers).where(store.scope(m.business_customers))
        ).mappings()
    ]
    debts = [
        {**r, "remaining_paise": outstanding(rows, r)}
        for r in rows
        if r["kind"] in ("opening_due", "credit_sale", "payable")
    ]
    for p in people:
        sales = [
            r
            for r in rows
            if r["customer_id"] == p["id"] and r["kind"] in ("credit_sale", "cash_sale")
        ]
        p.update(
            outstanding_paise=sum(
                d["remaining_paise"] for d in debts if d["customer_id"] == p["id"]
            ),
            recorded_sale_count=len(sales),
            last_recorded_sale=max((r["occurred_on"] for r in sales), default=None),
            segment="repeat_recorded"
            if len(sales) >= 2
            else "one_recorded"
            if sales
            else "no_recorded_sales",
        )
    for p in people:
        last = p["last_recorded_sale"]
        p["days_since_recorded_sale"] = (today() - last).days if last else None
        p["no_recorded_sale_in_30_days"] = last is not None and (today() - last).days >= 30
    opening = next((r for r in rows if r["kind"] == "opening_cash"), None)
    ins = sum(
        r["amount_paise"]
        for r in rows
        if r["kind"] in ("opening_cash", "cash_sale", "collection")
        and r["payment_channel"] == "cash"
    )
    outs = sum(
        r["amount_paise"]
        for r in rows
        if r["kind"] in ("expense", "payable_payment") and r["payment_channel"] == "cash"
    )
    expenses = {
        c: sum(r["amount_paise"] for r in rows if r["kind"] == "expense" and r["category"] == c)
        for c in ("stock", "rent", "utilities", "wages", "transport", "other")
    }
    return {
        "mode": "demo" if auth.current().demo else "manual",
        "as_of": today(),
        "customers": people,
        "obligations": debts,
        "entries": [
            {**r, "reversed": any(x["reversal_of"] == r["id"] for x in history)}
            for r in history[-100:][::-1]
        ],
        "history_limit": 100,
        "active_entry_count": len(rows),
        "cash": {
            "opening_recorded": opening is not None,
            "recorded_balance_paise": ins - outs if opening else None,
            "net_recorded_movement_paise": ins - outs - (opening["amount_paise"] if opening else 0),
            "warning": "Manual cash movements only. This is not a bank balance, profit or a complete cash forecast.",
        },
        "sales_paise": sum(
            r["amount_paise"] for r in rows if r["kind"] in ("cash_sale", "credit_sale")
        ),
        "expenses_by_category": expenses,
        "source": "merchant_reviewed_manual",
        "sales_coverage_verified": False,
        "external_sending_enabled": False,
        "forecast_enabled": False,
    }


@router.get("/summary")
def summary():
    with store.connect() as db:
        return build_summary(db)


def entry_view(db, row):
    return {
        **row,
        "reversed": bool(
            db.execute(
                select(m.business_entries.c.id).where(
                    store.scope(m.business_entries), m.business_entries.c.reversal_of == row["id"]
                )
            ).first()
        ),
        "source": "merchant_reviewed_manual",
    }


@router.get("/entries")
def entry_sources(
    group: Literal["all", "sales", "expenses"] = "all",
    on: date | None = None,
    offset: int = Query(default=0, ge=0, le=10000),
):
    with store.connect() as db:
        history = all_entries(db)
        rows = history if group == "all" else active_entries(db, history)
        if group != "all":
            allowed = ("cash_sale", "credit_sale") if group == "sales" else ("expense",)
            rows = [r for r in rows if r["kind"] in allowed]
        if on is not None:
            rows = [r for r in rows if r["occurred_on"] == on]
        rows = rows[::-1]
        return {
            "items": [entry_view(db, r) for r in rows[offset : offset + 50]],
            "total_count": len(rows),
            "next_offset": offset + 50 if offset + 50 < len(rows) else None,
            "group": group,
            "on": on,
            "source": "merchant_reviewed_manual",
        }


@router.get("/entries/{eid}")
def entry_source(eid: str):
    with store.connect() as db:
        return entry_view(db, get(db, m.business_entries, eid))


@router.get("/customers/{eid}")
def customer_source(eid: str):
    with store.connect() as db:
        person = get(db, m.business_customers, eid)
        rows = active_entries(db)
        debts = [
            {**r, "remaining_paise": outstanding(rows, r)}
            for r in rows
            if r["customer_id"] == eid and r["kind"] in ("opening_due", "credit_sale")
        ]
        return {
            **person,
            "obligations": debts,
            "outstanding_paise": sum(r["remaining_paise"] for r in debts),
            "source": "merchant_reviewed_manual",
        }


@router.get("/tasks/{eid}")
def task_source(eid: str):
    with store.connect() as db:
        return get(db, m.business_tasks, eid)


@router.post("/customers/{eid}/reminder")
def reminder(eid: str):
    with store.connect("messaging") as db:
        p = get(db, m.business_customers, eid)
        rows = active_entries(db)
        balance = sum(
            outstanding(rows, r)
            for r in rows
            if r["customer_id"] == eid and r["kind"] in ("opening_due", "credit_sale")
        )
        if balance <= 0:
            raise RuleError("No recorded outstanding amount for this customer.")
        whole, cents = divmod(balance, 100)
        audit(db, eid, "Local customer reminder draft prepared; no message sent")
        return {
            "text": f"Hello {p['name']}, our manually reviewed records show INR {whole}.{cents:02d} pending. Please check this with us if anything differs. Thank you.",
            "amount_paise": balance,
            "review_required": True,
            "sent": False,
            "payment_link": None,
        }


@router.get("/tasks")
def tasks():
    with store.connect() as db:
        return [
            dict(r)
            for r in db.execute(
                select(m.business_tasks)
                .where(store.scope(m.business_tasks))
                .order_by(m.business_tasks.c.due_on)
            ).mappings()
        ]


@router.get("/staff")
def staff():
    with store.connect("admin") as db:
        return [
            dict(r)
            for r in db.execute(
                select(m.memberships.c.user_id, m.users.c.username, m.memberships.c.role)
                .join(m.users, m.users.c.id == m.memberships.c.user_id)
                .where(store.scope(m.memberships))
            ).mappings()
        ]


@router.post("/tasks", status_code=201)
def create_task(body: Task):
    with store.connect("write") as db:
        lock(db)
        assignee = body.assignee_id or auth.current().user_id
        if assignee != auth.current().user_id:
            auth.current("admin")
        member = db.execute(
            select(m.memberships.c.user_id).where(
                store.scope(m.memberships),
                m.memberships.c.user_id == assignee,
                m.memberships.c.role.in_(["owner", "staff"]),
            )
        ).first()
        if not member:
            raise RuleError("Choose an active owner or staff member in this store.")
        eid = store.uid()
        db.execute(
            insert(m.business_tasks).values(
                id=eid,
                store_id=auth.current().store_id,
                **body.model_dump(exclude={"assignee_id"}),
                assignee_id=assignee,
                status="open",
                version=1,
                created_at=now(),
            )
        )
        audit(db, eid, "Manual task created", 1)
        return get(db, m.business_tasks, eid)


@router.patch("/tasks/{eid}")
def task_status(eid: str, body: TaskStatus):
    with store.connect("write") as db:
        lock(db)
        old = get(db, m.business_tasks, eid)
        if old["assignee_id"] != auth.current().user_id:
            auth.current("admin")
        if old["version"] != body.version:
            raise RuleError("Task changed. Reload and review the current status.")
        db.execute(
            update(m.business_tasks)
            .where(store.scope(m.business_tasks), m.business_tasks.c.id == eid)
            .values(status=body.status, version=body.version + 1)
        )
        audit(db, eid, "Task " + body.status, body.version + 1)
        return get(db, m.business_tasks, eid)


@router.post("/campaigns", status_code=201)
def campaign(body: Campaign):
    with store.connect("messaging") as db:
        lock(db)
        if not body.merchant_confirmed or len(set(body.recipient_ids)) != len(body.recipient_ids):
            raise RuleError("Review unique recipients and this local draft first.")
        for eid in body.recipient_ids:
            if not get(db, m.business_customers, eid)["marketing_consent"]:
                raise RuleError("A selected customer has not agreed to marketing drafts.")
        eid = store.uid()
        db.execute(
            insert(m.business_campaigns).values(
                id=eid,
                store_id=auth.current().store_id,
                **body.model_dump(exclude={"merchant_confirmed"}),
                actor_id=auth.current().user_id,
                created_at=now(),
            )
        )
        audit(db, eid, "Local campaign draft saved; no sending integration")
        return {"id": eid, "status": "draft_only", "sent": False}


@router.get("/campaigns")
def campaigns():
    with store.connect("messaging") as db:
        result = []
        for r in db.execute(
            select(m.business_campaigns)
            .where(store.scope(m.business_campaigns))
            .order_by(m.business_campaigns.c.created_at.desc())
            .limit(100)
        ).mappings():
            eligible = [
                eid
                for eid in r["recipient_ids"]
                if get(db, m.business_customers, eid)["marketing_consent"]
            ]
            result.append(
                {
                    **dict(r),
                    "currently_eligible_recipient_ids": eligible,
                    "requires_recipient_review": eligible != r["recipient_ids"],
                    "sent": False,
                    "status": "draft_only",
                }
            )
        return result
