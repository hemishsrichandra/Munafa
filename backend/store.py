"""Tenant-scoped PostgreSQL repository. Core SQL lives here, never in route handlers."""

import hashlib
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
from sqlalchemy import select, insert, update, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from . import models as m
from .db import engine
from .auth import current
from .domain import RuleError, normalized

request_connection = ContextVar("request_connection", default=None)


def uid():
    return uuid.uuid4().hex


def scope(table):
    return table.c.store_id == current().store_id


def stamp(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def quantity(value):
    return (
        int(value)
        if value is not None and value == value.to_integral()
        else (str(value) if value is not None else None)
    )


@contextmanager
def connect(permission="read"):
    current(permission)
    try:
        active = request_connection.get()
        if active is not None:
            yield active
        else:
            with engine().begin() as db:
                yield db
    except IntegrityError:
        raise RuleError(
            "A duplicate reference or conflicting record already exists. Reload and review the existing case."
        ) from None


def all_cases(db=None):
    if db is None:
        with connect() as db:
            return all_cases(db)
    ids = db.execute(
        select(m.cases.c.id).where(scope(m.cases)).order_by(m.cases.c.created_at.desc())
    ).scalars()
    return [get(db, cid) for cid in ids]


def get(db, case_id, lock=False):
    q = select(m.cases).where(scope(m.cases), m.cases.c.id == case_id)
    if lock:
        q = q.with_for_update()
    row = db.execute(q).mappings().first()
    if not row:
        raise KeyError(case_id)
    c = dict(row)
    c.pop("store_id")
    c["created_at"] = c["created_at"].astimezone(timezone.utc).isoformat()
    c["follow_up"] = c["follow_up"].isoformat() if c["follow_up"] else None
    inv = (
        db.execute(
            select(m.invoices, m.suppliers.c.name, m.suppliers.c.phone)
            .join(
                m.suppliers,
                (m.suppliers.c.id == m.invoices.c.supplier_id)
                & (m.suppliers.c.store_id == m.invoices.c.store_id),
            )
            .where(scope(m.invoices), m.invoices.c.case_id == case_id)
        )
        .mappings()
        .one()
    )
    lines = []
    for line in db.execute(
        select(m.invoice_lines)
        .where(scope(m.invoice_lines), m.invoice_lines.c.invoice_id == inv["id"])
        .order_by(m.invoice_lines.c.position)
    ).mappings():
        lines.append(
            {
                k: quantity(line[k]) if k in ("billed", "received") else line[k]
                for k in (
                    "name",
                    "billed",
                    "received",
                    "unit",
                    "received_unit",
                    "unit_confirmed",
                    "price_paise",
                    "note",
                )
            }
        )
    c["invoice"] = {
        "supplier": inv["supplier_name"],
        "supplier_phone": inv["supplier_phone"],
        "reference": inv["reference"],
        "date": inv["date"].isoformat(),
        "pricing_note": inv["pricing_note"],
        "lines": lines,
    }
    c["resolutions"] = []
    for r in db.execute(
        select(m.resolutions)
        .where(scope(m.resolutions), m.resolutions.c.case_id == case_id)
        .order_by(m.resolutions.c.at, m.resolutions.c.id)
    ).mappings():
        c["resolutions"].append(
            {k: r[k] for k in ("id", "kind", "evidence_reference", "amount_paise", "attachment_id")}
            | {
                "supplier": inv["supplier_name"],
                "invoice_reference": inv["reference"],
                "applied_confirmed": True,
                "at": r["at"].astimezone(timezone.utc).isoformat(),
            }
        )
    c["history"] = []
    for event in db.execute(
        select(m.audit_events)
        .where(
            scope(m.audit_events),
            m.audit_events.c.entity_id == case_id,
            m.audit_events.c.entity_type == "case",
        )
        .order_by(m.audit_events.c.at, m.audit_events.c.id)
    ).mappings():
        e = {
            "at": event["at"].astimezone(timezone.utc).isoformat(),
            "action": event["action"],
            "detail": event["detail"],
        }
        if event["snapshot"] is not None:
            e["snapshot"] = event["snapshot"]
        c["history"].append(e)
    return c


def audit_record(
    db,
    entity_id,
    action,
    prior=None,
    new=None,
    source_ids=None,
    snapshot=None,
    detail="",
    entity_type="case",
    at=None,
):
    p = current()
    db.execute(
        insert(m.audit_events).values(
            id=uid(),
            store_id=p.store_id,
            actor_id=p.user_id,
            entity_id=entity_id,
            entity_type=entity_type,
            action=action,
            prior_version=prior,
            new_version=new,
            source_ids=source_ids or [entity_id],
            snapshot=snapshot,
            detail=detail,
            at=stamp(at) if at else datetime.now(timezone.utc),
        )
    )


def save(db, c):
    p = current("write")
    old = (
        db.execute(select(m.cases).where(scope(m.cases), m.cases.c.id == c["id"]))
        .mappings()
        .first()
    )
    values = {
        k: c[k]
        for k in (
            "status",
            "version",
            "synthetic",
            "delivery_complete",
            "pricing_confirmed",
            "approved_version",
            "approved_amount_paise",
            "promise",
            "attachment_id",
        )
    }
    if c["synthetic"] != p.demo:
        raise RuleError("Demo and live records must use separate stores.")
    values.update(
        created_at=stamp(c["created_at"]),
        follow_up=date.fromisoformat(c["follow_up"]) if c["follow_up"] else None,
    )
    if old:
        oldcase = get(db, c["id"])
        if c["history"][: len(oldcase["history"])] != oldcase["history"]:
            raise RuleError("Historical events cannot be rewritten.")
        if c["resolutions"][: len(oldcase["resolutions"])] != oldcase["resolutions"]:
            raise RuleError("Recovery records cannot be rewritten.")
        db.execute(update(m.cases).where(scope(m.cases), m.cases.c.id == c["id"]).values(**values))
    else:
        oldcase = {"history": [], "resolutions": []}
        db.execute(insert(m.cases).values(id=c["id"], store_id=p.store_id, **values))
    inv = c["invoice"]
    key = normalized(inv["supplier"])
    supplier = db.execute(
        pg_insert(m.suppliers)
        .values(
            id=uid(),
            store_id=p.store_id,
            name=inv["supplier"],
            name_key=key,
            phone=inv.get("supplier_phone", ""),
        )
        .on_conflict_do_update(
            index_elements=["store_id", "name_key"],
            set_={"name": inv["supplier"], "phone": inv.get("supplier_phone", "")},
        )
        .returning(m.suppliers.c.id)
    ).scalar_one()
    existing = (
        db.execute(select(m.invoices).where(scope(m.invoices), m.invoices.c.case_id == c["id"]))
        .mappings()
        .first()
    )
    ival = {
        "supplier_id": supplier,
        "supplier_name": inv["supplier"],
        "supplier_phone": inv.get("supplier_phone", ""),
        "reference": inv["reference"],
        "reference_key": normalized(inv["reference"]),
        "date": date.fromisoformat(inv["date"]),
        "pricing_note": inv["pricing_note"],
    }
    if existing:
        iid = existing["id"]
        db.execute(
            update(m.invoices).where(scope(m.invoices), m.invoices.c.id == iid).values(**ival)
        )
        db.execute(
            delete(m.invoice_lines).where(
                scope(m.invoice_lines), m.invoice_lines.c.invoice_id == iid
            )
        )
    else:
        iid = uid()
        db.execute(insert(m.invoices).values(id=iid, store_id=p.store_id, case_id=c["id"], **ival))
    for i, line in enumerate(inv["lines"]):
        db.execute(
            insert(m.invoice_lines).values(
                id=uid(), store_id=p.store_id, invoice_id=iid, position=i, **line
            )
        )
    for event in c["history"][len(oldcase["history"]) :]:
        audit_record(
            db,
            c["id"],
            event["action"],
            old["version"] if old else None,
            c["version"],
            snapshot=event.get("snapshot"),
            detail=event["detail"],
            at=event["at"],
        )
    for r in c["resolutions"][len(oldcase["resolutions"]) :]:
        proof = attachment(db, r["attachment_id"], c["id"])
        if not proof:
            raise RuleError("Attach evidence belonging to this case.")
        db.execute(
            insert(m.resolutions).values(
                id=r["id"],
                store_id=p.store_id,
                case_id=c["id"],
                supplier_id=supplier,
                kind=r["kind"],
                evidence_reference=r["evidence_reference"],
                reference_key=normalized(r["evidence_reference"]),
                amount_paise=r["amount_paise"],
                attachment_id=r["attachment_id"],
                proof_digest=proof["digest"],
                at=stamp(r["at"]),
            )
        )
        db.execute(
            insert(m.financial_events).values(
                id=uid(),
                store_id=p.store_id,
                case_id=c["id"],
                resolution_id=r["id"],
                amount_paise=r["amount_paise"],
                at=stamp(r["at"]),
            )
        )


@contextmanager
def mutate(case_id, version, permission="write"):
    with connect(permission) as db:
        c = get(db, case_id, True)
        if c["version"] != version:
            raise RuleError("This case changed in another tab. Reload it and try again.")
        yield db, c
        c["version"] += 1
        save(db, c)


def add_attachment(db, case_id, name, mime, data, fields=None):
    current("write")
    get(db, case_id)
    aid = uid()
    db.execute(
        insert(m.attachments).values(
            id=aid,
            store_id=current().store_id,
            case_id=case_id,
            name=name[:200],
            mime=mime,
            data=data,
            digest=hashlib.sha256(data).hexdigest(),
            synthetic_fields=fields,
            created_at=datetime.now(timezone.utc),
        )
    )
    return aid


def attachment(db, aid, case_id=None):
    q = select(m.attachments).where(scope(m.attachments), m.attachments.c.id == aid)
    if case_id:
        q = q.where(m.attachments.c.case_id == case_id)
    return db.execute(q).mappings().first()


def proof_used(db, supplier, reference=None, digest=None):
    q = (
        select(m.resolutions.c.id)
        .join(
            m.suppliers,
            (m.suppliers.c.id == m.resolutions.c.supplier_id)
            & (m.suppliers.c.store_id == m.resolutions.c.store_id),
        )
        .where(scope(m.resolutions), m.suppliers.c.name_key == normalized(supplier))
    )
    q = (
        q.where(m.resolutions.c.reference_key == normalized(reference))
        if reference is not None
        else q.where(m.resolutions.c.proof_digest == digest)
    )
    return db.execute(q).first() is not None
