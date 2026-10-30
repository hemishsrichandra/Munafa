"""Scoped SKU catalog and immutable quantity events. Payments are never sales evidence."""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, insert, update, func
from . import models as m, store, auth
from .domain import RuleError, local_today
from .commerce_models import ProductInput, ConversionInput, MovementInput


def quantity(q):
    return format(Decimal(q), "f").rstrip("0").rstrip(".") if Decimal(q) % 1 else str(int(q))


def exact(q):
    q = Decimal(q)
    if (
        not q.is_finite()
        or q != q.quantize(Decimal("0.000001"))
        or abs(q) >= Decimal("100000000000000")
    ):
        raise RuleError(
            "Converted quantity cannot be represented exactly at six decimal places. Review units; no rounding was applied."
        )
    return q


def product(db, pid, lock=False):
    q = select(m.products).where(store.scope(m.products), m.products.c.id == pid)
    row = db.execute(q.with_for_update() if lock else q).mappings().first()
    if not row:
        raise KeyError(pid)
    return dict(row)


def balance(db, pid, lot_id=None, lot_specific=False):
    q = select(func.coalesce(func.sum(m.inventory_events.c.quantity_delta), 0)).where(
        store.scope(m.inventory_events), m.inventory_events.c.product_id == pid
    )
    if lot_specific:
        q = q.where(m.inventory_events.c.lot_id == lot_id)
    return Decimal(db.execute(q).scalar_one())


def product_view(db, row):
    stock = balance(db, row["id"])
    return {
        **row,
        "created_at": row["created_at"].isoformat(),
        "stock_quantity": quantity(stock),
        "reorder_threshold": quantity(row["reorder_threshold"])
        if row["reorder_threshold"] is not None
        else None,
        "below_threshold": row["reorder_threshold"] is not None
        and stock <= row["reorder_threshold"],
        "synthetic": auth.current().demo,
        "stock_state": "server_confirmed",
    }


def products(db):
    return [
        product_view(db, dict(r))
        for r in db.execute(
            select(m.products).where(store.scope(m.products)).order_by(m.products.c.name)
        ).mappings()
    ]


def create_product(db, body: ProductInput):
    p = auth.current("write")
    pid = store.uid()
    db.execute(
        insert(m.products).values(
            id=pid,
            store_id=p.store_id,
            **body.model_dump(),
            version=1,
            stock_version=0,
            created_at=datetime.now(timezone.utc),
        )
    )
    store.audit_record(db, pid, "SKU created", new=1, entity_type="product")
    return product_view(db, product(db, pid))


def change_product(db, pid, version, body):
    p = product(db, pid, True)
    if p["version"] != version:
        raise RuleError("SKU changed. Reload before editing.")
    if body.unit != p["unit"]:
        raise RuleError(
            "Stock unit is fixed. Create a separate SKU instead of reinterpreting existing quantities."
        )
    db.execute(
        update(m.products)
        .where(store.scope(m.products), m.products.c.id == pid)
        .values(**body.model_dump(), version=version + 1)
    )
    store.audit_record(db, pid, "SKU reviewed", version, version + 1, entity_type="product")
    return product_view(db, product(db, pid))


def add_conversion(db, pid, body: ConversionInput):
    auth.current("approve")
    p = product(db, pid, True)
    if body.from_unit == body.to_unit:
        raise RuleError("A conversion requires different units.")
    cid = store.uid()
    db.execute(
        insert(m.conversions).values(
            id=cid,
            store_id=auth.current().store_id,
            product_id=pid,
            **body.model_dump(),
            created_by=auth.current().user_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.execute(
        update(m.products)
        .where(store.scope(m.products), m.products.c.id == pid)
        .values(version=p["version"] + 1)
    )
    store.audit_record(
        db,
        cid,
        "Merchant unit conversion defined",
        source_ids=[pid, cid],
        snapshot=body.model_dump(mode="json"),
        entity_type="unit_conversion",
    )
    return {"id": cid, **body.model_dump(mode="json")}


def convert(db, pid, q, source_unit, target_unit):
    if source_unit == target_unit:
        return exact(q), []
    row = (
        db.execute(
            select(m.conversions).where(
                store.scope(m.conversions),
                m.conversions.c.product_id == pid,
                m.conversions.c.from_unit == source_unit,
                m.conversions.c.to_unit == target_unit,
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise RuleError(
            f"No merchant-defined {source_unit} → {target_unit} conversion. Units have not been inferred."
        )
    return exact(Decimal(q) * row["factor"]), [row["id"]]


def lots(db, pid):
    product(db, pid)
    result = []
    for r in db.execute(
        select(m.inventory_lots)
        .where(store.scope(m.inventory_lots), m.inventory_lots.c.product_id == pid)
        .order_by(m.inventory_lots.c.created_at)
    ).mappings():
        result.append(
            {
                **r,
                "created_at": r["created_at"].isoformat(),
                "expiry_date": r["expiry_date"].isoformat() if r["expiry_date"] else None,
                "quantity": quantity(balance(db, pid, r["id"], True)),
            }
        )
    return result


def make_lot(db, p, source_id, batch_reference, expiry_date):
    if not (p["expiry_tracking"] or batch_reference or expiry_date):
        return None
    if batch_reference:
        old = (
            db.execute(
                select(m.inventory_lots)
                .where(
                    store.scope(m.inventory_lots),
                    m.inventory_lots.c.product_id == p["id"],
                    m.inventory_lots.c.batch_reference == batch_reference,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if old:
            if old["expiry_date"] != expiry_date:
                raise RuleError(
                    "This batch reference already has a different recorded expiry. Do not overwrite its history."
                )
            return old["id"]
    lid = store.uid()
    db.execute(
        insert(m.inventory_lots).values(
            id=lid,
            store_id=auth.current().store_id,
            product_id=p["id"],
            source_id=source_id,
            batch_reference=batch_reference,
            expiry_date=expiry_date,
            created_at=datetime.now(timezone.utc),
        )
    )
    return lid


def source(
    db, pid, kind, entity_id, reference, occurred_on, reason, snapshot, case_id=None, sid=None
):
    sid = sid or store.uid()
    p = auth.current("approve")
    db.execute(
        insert(m.inventory_sources).values(
            id=sid,
            store_id=p.store_id,
            product_id=pid,
            source_type=kind,
            source_entity_id=entity_id,
            reference=reference,
            occurred_on=occurred_on,
            reason=reason,
            case_id=case_id,
            snapshot=snapshot,
            actor_id=p.user_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    return sid


def append_event(db, p, source_id, kind, delta, operation_id, lot_id=None, reversal_of=None):
    auth.current("approve")
    delta = exact(delta)
    if balance(db, p["id"]) + delta < 0 or balance(db, p["id"], lot_id, True) + delta < 0:
        raise RuleError(
            "This event would make recorded stock or its selected batch negative. Count/review actual stock first."
        )
    eid = store.uid()
    previous = p["stock_version"]
    db.execute(
        insert(m.inventory_events).values(
            id=eid,
            store_id=auth.current().store_id,
            product_id=p["id"],
            source_id=source_id,
            lot_id=lot_id,
            kind=kind,
            quantity_delta=delta,
            unit=p["unit"],
            operation_id=operation_id,
            reversal_of=reversal_of,
            prior_version=previous,
            new_version=previous + 1,
            actor_id=auth.current().user_id,
            at=datetime.now(timezone.utc),
        )
    )
    db.execute(
        update(m.products)
        .where(store.scope(m.products), m.products.c.id == p["id"])
        .values(stock_version=previous + 1)
    )
    p["stock_version"] = previous + 1
    store.audit_record(
        db,
        eid,
        "Inventory event accepted",
        previous,
        previous + 1,
        source_ids=[source_id, p["id"]],
        entity_type="inventory_event",
    )
    return eid


def movement_payload(db, raw, lock=False):
    body = MovementInput.model_validate(raw)
    p = product(db, body.product_id, lock)
    if p["stock_version"] != body.expected_stock_version:
        raise RuleError(
            "Stock changed. Review the latest confirmed quantity and version; no overwrite was applied."
        )
    if body.occurred_on > local_today():
        raise RuleError("A stock movement needs an actual occurrence date, not a future promise.")
    lot = None
    if body.lot_id:
        lot = (
            db.execute(
                select(m.inventory_lots).where(
                    store.scope(m.inventory_lots),
                    m.inventory_lots.c.id == body.lot_id,
                    m.inventory_lots.c.product_id == p["id"],
                )
            )
            .mappings()
            .first()
        )
        if not lot:
            raise KeyError(body.lot_id)
        if body.expiry_date and body.expiry_date != lot["expiry_date"]:
            raise RuleError("Recorded lot expiry cannot be edited through a movement.")
    if (
        not lot
        and body.batch_reference
        and db.execute(
            select(m.inventory_lots.c.id).where(
                store.scope(m.inventory_lots),
                m.inventory_lots.c.product_id == p["id"],
                m.inventory_lots.c.batch_reference == body.batch_reference,
            )
        ).first()
    ):
        raise RuleError("Select the existing recorded batch rather than creating it again.")
    new_lot = not lot and bool(p["expiry_tracking"] or body.batch_reference or body.expiry_date)
    if (
        body.kind in ("count", "shortage_correction")
        and not lot
        and any(Decimal(entry["quantity"]) > 0 for entry in lots(db, p["id"]))
        and not body.batch_reference
    ):
        raise RuleError(
            "Count one recorded batch, or identify a genuinely new batch. A total count must not double-count existing lots."
        )
    value, conversion_ids = convert(db, p["id"], body.quantity, body.unit, p["unit"])
    current = Decimal(0) if new_lot else balance(db, p["id"], body.lot_id, True)
    if body.kind in ("count", "shortage_correction"):
        delta = value - current
    elif body.kind in ("sale", "return_out", "damage"):
        delta = -value
    elif body.kind == "return_in":
        delta = value
    else:
        original = (
            db.execute(
                select(m.inventory_events).where(
                    store.scope(m.inventory_events),
                    m.inventory_events.c.id == body.reversal_of,
                    m.inventory_events.c.product_id == p["id"],
                )
            )
            .mappings()
            .first()
        )
        if not original or original["kind"] == "reversal":
            raise RuleError("Choose an accepted, unreversed movement to correct.")
        if db.execute(
            select(m.inventory_events.c.id).where(
                store.scope(m.inventory_events), m.inventory_events.c.reversal_of == original["id"]
            )
        ).first():
            raise RuleError("This movement already has its reversal.")
        if body.quantity != 0 or body.lot_id != original["lot_id"]:
            raise RuleError(
                "A reversal must use its original batch and zero entered quantity; the exact opposite event is derived by the server."
            )
        delta = -original["quantity_delta"]
        new_lot = False
    if body.kind not in ("count", "shortage_correction") and delta == 0:
        raise RuleError("Record a positive movement quantity.")
    if new_lot and delta < 0:
        raise RuleError("Choose the actual existing batch for stock leaving inventory.")
    if body.kind == "shortage_correction":
        if not body.case_id:
            raise RuleError(
                "A shortage correction must link an approved claim and a separately confirmed physical count."
            )
        c = store.get(db, body.case_id)
        link = db.execute(
            select(m.purchases.c.id)
            .join(
                m.purchase_lines,
                (m.purchase_lines.c.purchase_id == m.purchases.c.id)
                & (m.purchase_lines.c.store_id == m.purchases.c.store_id),
            )
            .where(
                store.scope(m.purchases),
                m.purchases.c.case_id == c["id"],
                m.purchase_lines.c.product_id == p["id"],
            )
        ).first()
        if c["approved_version"] is None or not link:
            raise RuleError("This SKU is not linked to an approved purchase shortage claim.")
    elif body.case_id:
        raise RuleError("Use the explicit shortage-correction count type to link a claim.")
    if balance(db, p["id"]) + delta < 0 or (not new_lot and current + delta < 0):
        raise RuleError("Recorded stock would become negative. Review the actual count instead.")
    return {
        "input": body.model_dump(mode="json"),
        "product_version": p["version"],
        "stock_version": p["stock_version"],
        "stock_unit": p["unit"],
        "current_quantity": quantity(current),
        "quantity_delta": quantity(exact(delta)),
        "conversion_ids": conversion_ids,
        "new_lot": new_lot,
    }


def execute_movement(db, payload, operation_id):
    body = MovementInput.model_validate(payload["input"])
    p = product(db, body.product_id, True)
    checked = movement_payload(db, body.model_dump(mode="json"))
    if checked != payload:
        raise RuleError("The approved stock proposal changed. Review a fresh proposal.")
    sid = source(
        db,
        p["id"],
        body.kind,
        store.uid(),
        body.reference,
        body.occurred_on,
        body.reason,
        checked,
        body.case_id,
    )
    lid = body.lot_id
    if checked["new_lot"]:
        lid = make_lot(db, p, sid, body.batch_reference, body.expiry_date)
    eid = append_event(
        db,
        p,
        sid,
        body.kind,
        Decimal(checked["quantity_delta"]),
        operation_id,
        lid,
        body.reversal_of,
    )
    return {"event_id": eid, "product": product_view(db, product(db, p["id"]))}


def movements(db, pid):
    p = product(db, pid)
    rows = db.execute(
        select(
            m.inventory_events,
            m.inventory_sources.c.reference,
            m.inventory_sources.c.reason,
            m.inventory_sources.c.occurred_on,
            m.inventory_sources.c.source_entity_id,
            m.inventory_sources.c.case_id,
        )
        .join(
            m.inventory_sources,
            (m.inventory_sources.c.id == m.inventory_events.c.source_id)
            & (m.inventory_sources.c.store_id == m.inventory_events.c.store_id),
        )
        .where(store.scope(m.inventory_events), m.inventory_events.c.product_id == pid)
        .order_by(m.inventory_events.c.new_version.desc())
    ).mappings()
    return {
        "product": product_view(db, p),
        "events": [
            {
                **r,
                "quantity_delta": quantity(r["quantity_delta"]),
                "at": r["at"].isoformat(),
                "occurred_on": r["occurred_on"].isoformat(),
            }
            for r in rows
        ],
        "lots": lots(db, pid),
    }
