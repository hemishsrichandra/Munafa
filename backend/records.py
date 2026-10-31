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


def entry_view(db, row, history=None):
    history = all_entries(db) if history is None else history
    active = active_entries(db, history)
    reversed_ids = {r["reversal_of"] for r in history if r["reversal_of"]}
    allocations = [
        {**r, "reversed": r["id"] in reversed_ids} for r in history if r["target_id"] == row["id"]
    ]
    remaining = (
        (outstanding(active, row) if row["id"] not in reversed_ids else 0)
        if row["kind"] in ("opening_due", "credit_sale", "payable")
        else None
    )
    return {
        **row,
        "reversed": row["id"] in reversed_ids,
        "remaining_paise": remaining,
        "allocations": allocations,
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
            "items": [entry_view(db, r, history=history) for r in rows[offset : offset + 50]],
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
        amount_str = f"{whole}.{cents:02d}" if cents else str(whole)

        # Fetch store settings (may not exist yet for older stores)
        principal = auth.current()
        settings_row = (
            db.execute(
                select(m.store_settings).where(m.store_settings.c.store_id == principal.store_id)
            )
            .mappings()
            .first()
        )
        upi_vpa = settings_row["upi_vpa"] if settings_row else None
        lang = (settings_row["reminder_language"] if settings_row else None) or "en"

        store_name = principal.store_name

        # Multilingual reminder templates — merchant must review before sending
        templates = {
            "en": (
                f"Namaste {p['name']} ji, our records show INR {amount_str} pending "
                f"(\u20b9{amount_str}) at {store_name}. Kindly settle at your convenience. Thank you!"
            ),
            "hi": (
                f"\u0928\u092e\u0938\u094d\u0924\u0947 {p['name']} \u091c\u0940, "
                f"{store_name} \u092e\u0947\u0902 \u0906\u092a\u0915\u093e \u092c\u0915\u093e\u092f\u093e "
                f"\u0930\u093e\u0936\u093f INR {amount_str} (\u20b9{amount_str}) \u0939\u0948\u0964 "
                f"\u0915\u0943\u092a\u092f\u093e \u0938\u0941\u0935\u093f\u0927\u093e\u0928\u0941\u0938\u093e\u0930 "
                f"\u091c\u092e\u093e \u0915\u0930\u0947\u0902\u0964 \u0927\u0928\u094d\u092f\u0935\u093e\u0926!"
            ),
            "kn": (
                f"\u0ca8\u0cae\u0cb8\u0ccd\u0c95\u0cbe\u0cb0 {p['name']} \u0c85\u0cb5\u0cb0\u0cc7, "
                f"{store_name} \u0ca8\u0cb2\u0ccd\u0cb2\u0cbf \u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0cac\u0cbe\u0c95\u0cbf "
                f"INR {amount_str} (\u20b9{amount_str}) \u0c87\u0ca6\u0cc6. \u0c85\u0ca8\u0cc1\u0c95\u0cc2\u0cb2\u0cb5\u0cbe\u0c97\u0cbf "
                f"\u0caa\u0ca1\u0cc6 \u0cae\u0cbe\u0ca1\u0cbf. \u0ca7\u0ca8\u0ccd\u0caf\u0cb5\u0cbe\u0ca6\u0c97\u0cb3\u0cc1!"
            ),
        }
        text = templates.get(lang, templates["en"])

        # Build UPI deep link if store VPA is configured
        payment_link = None
        upi_display = None
        if upi_vpa:
            import urllib.parse

            clean_store = store_name.replace(" ", "")
            params = f"pa={upi_vpa}&pn={urllib.parse.quote(clean_store)}&am={amount_str}&cu=INR"
            payment_link = f"upi://pay?{params}"
            if lang == "hi":
                text_with_link = (
                    f"\u0928\u092e\u0938\u094d\u0924\u0947 {p['name']} \u091c\u0940, {store_name} \u092e\u0947\u0902 "
                    f"\u0906\u092a\u0915\u093e \u092c\u0915\u093e\u092f\u093e \u0930\u093e\u0936\u093f \u20b9{amount_str} \u0939\u0948\u0964 "
                    f"\u0915\u0943\u092a\u092f\u093e \u0907\u0938 UPI \u0932\u093f\u0902\u0915 \u0938\u0947 \u092d\u0941\u0917\u0924\u093e\u0928 \u0915\u0930\u0947\u0902: {payment_link}\u0964 \u0927\u0928\u094d\u092f\u0935\u093e\u0926!"
                )
            elif lang == "kn":
                text_with_link = (
                    f"\u0ca8\u0cae\u0cb8\u0ccd\u0c95\u0cbe\u0cb0 {p['name']} \u0c85\u0cb5\u0cb0\u0cc7, {store_name} \u0ca8\u0cb2\u0ccd\u0cb2\u0cbf "
                    f"\u0ca8\u0cbf\u0cae\u0ccd\u0cae \u0cac\u0cbe\u0c95\u0cbf \u20b9{amount_str} \u0c87\u0ca6\u0cc6. "
                    f"\u0ca6\u0caf\u0cb5\u0cbf\u0c9f\u0ccd\u0c9f\u0cc1 \u0c88 UPI \u0cb2\u0cbf\u0c82\u0c95\u0ccd \u0cac\u0cb3\u0cb8\u0cbf \u0caa\u0cbe\u0cb5\u0ca4\u0cbf\u0cb8\u0cbf: {payment_link}. \u0ca7\u0ca8\u0ccd\u0caf\u0cb5\u0cbe\u0ca6\u0c97\u0cb3\u0cc1!"
                )
            else:
                text_with_link = (
                    f"Namaste {p['name']} ji, our records show INR {amount_str} pending "
                    f"(\u20b9{amount_str}) at {store_name}. Kindly pay using this UPI link: {payment_link}. Thank you!"
                )
            upi_display = payment_link
        else:
            text_with_link = text

        audit(db, eid, "Local customer reminder draft prepared; no message sent")
        return {
            "text": text_with_link,
            "text_plain": text,
            "amount_paise": balance,
            "customer_name": p["name"],
            "customer_phone": p["phone"],
            "store_name": store_name,
            "upi_vpa": upi_vpa,
            "payment_link": upi_display,
            "lang": lang,
            "review_required": True,
            "sent": False,
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


# ---------------------------------------------------------------------------
# Store settings (UPI VPA + reminder language) — Feature 1
# ---------------------------------------------------------------------------


class StoreSettingsInput(StrictModel):
    upi_vpa: str | None = None
    reminder_language: str = "en"


@router.get("/store-settings")
def get_store_settings():
    with store.connect() as db:
        sid = auth.current().store_id
        row = (
            db.execute(select(m.store_settings).where(m.store_settings.c.store_id == sid))
            .mappings()
            .first()
        )
        if not row:
            return {"upi_vpa": None, "reminder_language": "en"}
        return {"upi_vpa": row["upi_vpa"], "reminder_language": row["reminder_language"]}


@router.patch("/store-settings")
def update_store_settings(body: StoreSettingsInput):
    if body.reminder_language not in ("en", "hi", "kn"):
        raise RuleError("Reminder language must be en, hi or kn.")
    if body.upi_vpa is not None:
        import re

        if not re.fullmatch(r"[a-zA-Z0-9.\-_@]{3,120}", body.upi_vpa or ""):
            raise RuleError("Enter a valid UPI VPA (e.g. storename@paytm).")
    with store.connect("write") as db:
        sid = auth.current("write").store_id
        existing = (
            db.execute(select(m.store_settings).where(m.store_settings.c.store_id == sid))
            .mappings()
            .first()
        )
        from datetime import datetime, timezone
        from sqlalchemy import insert, update as sa_update

        now = datetime.now(timezone.utc)
        if existing:
            db.execute(
                sa_update(m.store_settings)
                .where(m.store_settings.c.store_id == sid)
                .values(
                    upi_vpa=body.upi_vpa,
                    reminder_language=body.reminder_language,
                    updated_at=now,
                )
            )
        else:
            db.execute(
                insert(m.store_settings).values(
                    store_id=sid,
                    upi_vpa=body.upi_vpa,
                    reminder_language=body.reminder_language,
                    updated_at=now,
                )
            )
        store.audit_record(db, sid, "Store settings updated", entity_type="store_settings")
        return {"upi_vpa": body.upi_vpa, "reminder_language": body.reminder_language}


# ---------------------------------------------------------------------------
# Galla Hisab (Nightly Cash Drawer Balancing) — Feature 2
# ---------------------------------------------------------------------------


class GallaHisabCheck(StrictModel):
    counted_cash_paise: int = Field(ge=0, le=1000000000000, strict=True)


@router.get("/galla-hisab")
def get_galla_hisab():
    with store.connect() as db:
        rows = active_entries(db)
        today_date = today()
        opening = next((r for r in rows if r["kind"] == "opening_cash"), None)
        opening_paise = opening["amount_paise"] if opening else 0

        today_cash_sales = sum(
            r["amount_paise"]
            for r in rows
            if r["kind"] == "cash_sale"
            and r["occurred_on"] == today_date
            and r["payment_channel"] == "cash"
        )
        today_cash_collections = sum(
            r["amount_paise"]
            for r in rows
            if r["kind"] == "collection"
            and r["occurred_on"] == today_date
            and r["payment_channel"] == "cash"
        )
        today_expenses_rows = [
            r
            for r in rows
            if r["kind"] in ("expense", "payable_payment")
            and r["occurred_on"] == today_date
            and r["payment_channel"] == "cash"
        ]
        today_cash_expenses = sum(r["amount_paise"] for r in today_expenses_rows)

        expected_cash_paise = max(
            0, opening_paise + today_cash_sales + today_cash_collections - today_cash_expenses
        )

        expense_breakdown = {}
        for r in today_expenses_rows:
            cat = r.get("category", "other")
            expense_breakdown[cat] = expense_breakdown.get(cat, 0) + r["amount_paise"]

        return {
            "as_of": today_date.isoformat(),
            "opening_cash_paise": opening_paise,
            "cash_sales_today_paise": today_cash_sales,
            "cash_collections_today_paise": today_cash_collections,
            "cash_expenses_today_paise": today_cash_expenses,
            "expected_cash_paise": expected_cash_paise,
            "expenses_breakdown": expense_breakdown,
            "has_opening_cash": opening is not None,
        }


@router.post("/galla-hisab/verify")
def verify_galla_hisab(body: GallaHisabCheck):
    with store.connect("write") as db:
        data = get_galla_hisab()
        expected = data["expected_cash_paise"]
        counted = body.counted_cash_paise
        diff = counted - expected

        if diff == 0:
            status = "balanced"
            badge = "Exact match! Cash drawer is balanced."
        elif diff < 0:
            status = "shortage"
            shortage_paise = abs(diff)
            w, c = divmod(shortage_paise, 100)
            shortage_str = f"₹{w}.{c:02d}" if c else f"₹{w}"
            badge = f"Shortage of {shortage_str} — Check for unrecorded cash payments or counting discrepancy."
        else:
            status = "surplus"
            surplus_paise = diff
            w, c = divmod(surplus_paise, 100)
            surplus_str = f"₹{w}.{c:02d}" if c else f"₹{w}"
            badge = (
                f"Surplus of {surplus_str} — Check for unrecorded sales or counting discrepancy."
            )

        audit(
            db,
            auth.current().store_id,
            f"Galla Hisab verified: counted {counted}, expected {expected}, status: {status}",
        )
        return {
            **data,
            "counted_cash_paise": counted,
            "difference_paise": diff,
            "status": status,
            "badge": badge,
        }
