"""Purchase review and physical receiving. Invoice acceptance never creates stock."""

import hashlib
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, insert, update, func
from . import models as m, store, auth, inventory
from .domain import RuleError, normalized, local_today, audit
from .commerce_models import PurchaseDraft, ReceivingDraft


def rounded(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get(db, pid, lock=False):
    q = select(m.purchases).where(store.scope(m.purchases), m.purchases.c.id == pid)
    row = db.execute(q.with_for_update() if lock else q).mappings().first()
    if not row:
        raise KeyError(pid)
    return dict(row)


def lines(db, pid):
    return [
        dict(r)
        for r in db.execute(
            select(m.purchase_lines)
            .where(store.scope(m.purchase_lines), m.purchase_lines.c.purchase_id == pid)
            .order_by(m.purchase_lines.c.position)
        ).mappings()
    ]


def checks(draft):
    d = PurchaseDraft.model_validate(draft)
    issues = []
    warnings = []
    subtotal = 0
    if not d.supplier:
        issues.append("Confirm the supplier.")
    if not d.reference:
        issues.append("Confirm the invoice reference.")
    try:
        date.fromisoformat(d.date)
    except ValueError:
        issues.append("Enter the actual invoice date.")
    for i, line in enumerate(d.lines):
        prefix = f"Item {i + 1}"
        for field, label in [
            ("description", "description"),
            ("billed_quantity", "billed quantity"),
            ("unit", "unit"),
            ("unit_price_paise", "printed unit price"),
            ("effective_price_paise", "effective claim unit price"),
            ("product_id", "reviewed SKU mapping"),
        ]:
            if getattr(line, field) is None or getattr(line, field) == "":
                issues.append(f"{prefix}: confirm {label}.")
        if line.billed_quantity is not None and line.unit_price_paise is not None:
            subtotal += rounded(line.billed_quantity * line.unit_price_paise)
        if line.confidence is None:
            warnings.append(
                f"{prefix}: extraction confidence not supplied; merchant review required."
            )
    if d.subtotal_paise is not None and d.subtotal_paise != subtotal:
        issues.append(
            "Recorded subtotal does not match billed quantity × printed unit prices (rounded per line)."
        )
    if d.tax_paise is None:
        issues.append("Record invoice tax, or explicitly enter zero if none is charged.")
    if d.discount_paise is None:
        issues.append("Record invoice discount, or explicitly enter zero.")
    for name, header in [("tax_paise", d.tax_paise), ("discount_paise", d.discount_paise)]:
        values = [getattr(entry, name) for entry in d.lines]
        if any(v is not None for v in values):
            if any(v is None for v in values):
                issues.append(
                    f"Complete each line’s {name.replace('_paise', '')} amount or remove incomplete line allocations and confirm the header."
                )
            elif header is not None and sum(values) != header:
                issues.append(
                    f"Line {name.replace('_paise', '')} amounts do not match the invoice header."
                )
    expected = subtotal + (d.tax_paise or 0) - (d.discount_paise or 0) + d.rounding_paise
    if d.total_paise is None:
        issues.append("Confirm the printed or manually recorded invoice total.")
    elif d.total_paise != expected:
        issues.append(
            "Invoice total does not reconcile with subtotal + recorded tax − discount + rounding."
        )
    if expected < 0:
        issues.append("Invoice total cannot be negative.")
    if d.tax_paise or d.discount_paise:
        warnings.append(
            "Effective claim prices are merchant-entered. No tax/discount allocation or unit conversion is inferred."
        )
    return {
        "subtotal_paise": subtotal,
        "expected_total_paise": expected,
        "issues": issues,
        "warnings": warnings,
        "eligible": not issues,
    }


def revision(db, p, snapshot, provenance):
    db.execute(
        insert(m.purchase_revisions).values(
            id=store.uid(),
            store_id=auth.current().store_id,
            purchase_id=p["id"],
            revision=p["version"],
            snapshot=snapshot,
            provenance=provenance,
            created_by=auth.current().user_id,
            created_at=datetime.now(timezone.utc),
        )
    )


def ensure_duplicate_free(db, d, pid=None):
    if not d.supplier or not d.reference:
        return
    for c in store.all_cases(db):
        if normalized(c["invoice"]["supplier"]) == normalized(d.supplier) and normalized(
            c["invoice"]["reference"]
        ) == normalized(d.reference):
            raise RuleError(
                f"Invoice already exists in supplier recovery case {c['id']}. Do not capture or stock it twice."
            )
    q = select(m.purchases.c.id).where(
        store.scope(m.purchases),
        m.purchases.c.supplier_key == normalized(d.supplier),
        m.purchases.c.reference_key == normalized(d.reference),
    )
    if pid:
        q = q.where(m.purchases.c.id != pid)
    if db.execute(q).first():
        raise RuleError("This supplier/reference already has a purchase draft or accepted record.")


def create(db, raw, source_kind="manual", document=None, provenance=None):
    auth.current("write")
    d = PurchaseDraft.model_validate(raw)
    ensure_duplicate_free(db, d)
    pid = store.uid()
    values = dict(
        id=pid,
        store_id=auth.current().store_id,
        case_id=None,
        status="draft",
        version=1,
        draft=d.model_dump(mode="json"),
        delivery_complete=False,
        source_kind=source_kind,
        created_by=auth.current().user_id,
        created_at=datetime.now(timezone.utc),
        supplier_key=normalized(d.supplier) or None,
        reference_key=normalized(d.reference) or None,
    )
    db.execute(insert(m.purchases).values(**values))
    prov = provenance or {"source": source_kind, "provider": None, "review_required": True}
    if document:
        name, mime, data = document
        did = store.uid()
        digest = hashlib.sha256(data).hexdigest()
        db.execute(
            insert(m.purchase_documents).values(
                id=did,
                store_id=auth.current().store_id,
                purchase_id=pid,
                name=name[:200],
                mime=mime,
                data=data,
                sha256=digest,
                created_at=datetime.now(timezone.utc),
            )
        )
        prov = {**prov, "document_id": did, "document_sha256": digest}
    revision(db, values, values["draft"], prov)
    store.audit_record(
        db,
        pid,
        "Purchase draft captured",
        new=1,
        entity_type="purchase",
        source_ids=[pid] + ([prov["document_id"]] if prov.get("document_id") else []),
    )
    return view(db, get(db, pid))


def revise(db, pid, version, raw, provenance=None):
    auth.current("write")
    p = get(db, pid, True)
    if p["version"] != version or p["status"] != "draft":
        raise RuleError(
            "Purchase is stale or already accepted. Accepted invoice evidence cannot be edited."
        )
    d = PurchaseDraft.model_validate(raw)
    ensure_duplicate_free(db, d, pid)
    p.update(
        version=version + 1,
        draft=d.model_dump(mode="json"),
        supplier_key=normalized(d.supplier) or None,
        reference_key=normalized(d.reference) or None,
    )
    db.execute(
        update(m.purchases)
        .where(store.scope(m.purchases), m.purchases.c.id == pid)
        .values(
            version=p["version"],
            draft=p["draft"],
            supplier_key=p["supplier_key"],
            reference_key=p["reference_key"],
        )
    )
    revision(
        db, p, p["draft"], provenance or {"source": "merchant_correction", "review_required": True}
    )
    store.audit_record(
        db, pid, "Purchase draft reviewed", version, version + 1, entity_type="purchase"
    )
    return view(db, p)


def document_metadata(db, pid):
    return [
        dict(r)
        for r in db.execute(
            select(
                m.purchase_documents.c.id,
                m.purchase_documents.c.name,
                m.purchase_documents.c.mime,
                m.purchase_documents.c.sha256,
            ).where(store.scope(m.purchase_documents), m.purchase_documents.c.purchase_id == pid)
        ).mappings()
    ]


def view(db, p):
    accepted = (
        db.execute(
            select(
                m.purchase_acceptances.c.snapshot,
                m.purchase_acceptances.c.total_paise,
                m.purchase_acceptances.c.accepted_at,
            ).where(
                store.scope(m.purchase_acceptances), m.purchase_acceptances.c.purchase_id == p["id"]
            )
        )
        .mappings()
        .first()
    )
    accepted_lines = lines(db, p["id"])
    for entry in accepted_lines:
        entry["billed_quantity"] = inventory.quantity(entry["billed_quantity"])
        if entry["tax_rate"] is not None:
            entry["tax_rate"] = inventory.quantity(entry["tax_rate"])
        qty = db.execute(
            select(func.coalesce(func.sum(m.receipt_lines.c.invoice_quantity), 0))
            .join(
                m.receipts,
                (m.receipts.c.id == m.receipt_lines.c.receipt_id)
                & (m.receipts.c.store_id == m.receipt_lines.c.store_id),
            )
            .where(
                store.scope(m.receipt_lines),
                m.receipts.c.purchase_id == p["id"],
                m.receipt_lines.c.purchase_line_id == entry["id"],
            )
        ).scalar_one()
        entry["received_quantity"] = inventory.quantity(qty)
        entry["receiving_state"] = "final" if p["delivery_complete"] else "not_final"
    revisions = [
        {**r, "created_at": r["created_at"].isoformat()}
        for r in db.execute(
            select(
                m.purchase_revisions.c.revision,
                m.purchase_revisions.c.provenance,
                m.purchase_revisions.c.created_at,
            )
            .where(store.scope(m.purchase_revisions), m.purchase_revisions.c.purchase_id == p["id"])
            .order_by(m.purchase_revisions.c.revision)
        ).mappings()
    ]
    rd = [
        {**r, "created_at": r["created_at"].isoformat()}
        for r in db.execute(
            select(m.receiving_drafts)
            .where(store.scope(m.receiving_drafts), m.receiving_drafts.c.purchase_id == p["id"])
            .order_by(m.receiving_drafts.c.created_at)
        ).mappings()
    ]
    receipts = [
        {**r, "accepted_at": r["accepted_at"].isoformat()}
        for r in db.execute(
            select(
                m.receipts.c.id,
                m.receipts.c.delivery_complete,
                m.receipts.c.payload,
                m.receipts.c.accepted_at,
            )
            .where(store.scope(m.receipts), m.receipts.c.purchase_id == p["id"])
            .order_by(m.receipts.c.accepted_at)
        ).mappings()
    ]
    return {
        **p,
        "created_at": p["created_at"].isoformat(),
        "checks": checks(p["draft"]),
        "documents": document_metadata(db, p["id"]),
        "revisions": revisions,
        "lines": accepted_lines,
        "receiving_drafts": rd,
        "receipts": receipts,
        "accepted_total_paise": accepted["total_paise"] if accepted else None,
        "accepted_at": accepted["accepted_at"].isoformat() if accepted else None,
        "synthetic": auth.current().demo,
    }


def acceptance_payload(db, pid, expected):
    p = get(db, pid)
    if p["version"] != expected or p["status"] != "draft":
        raise RuleError("Purchase source is stale or already accepted.")
    original = db.execute(
        select(m.purchase_revisions.c.provenance).where(
            store.scope(m.purchase_revisions),
            m.purchase_revisions.c.purchase_id == pid,
            m.purchase_revisions.c.revision == 1,
        )
    ).scalar_one()
    expected_document = original.get("expected_document")
    if expected_document and not any(
        d["sha256"] == expected_document["sha256"] for d in document_metadata(db, pid)
    ):
        raise RuleError(
            "The captured original document is still waiting to upload. Sync it before accepting the purchase."
        )
    calc = checks(p["draft"])
    if not calc["eligible"]:
        raise RuleError(" ".join(calc["issues"]))
    if date.fromisoformat(p["draft"]["date"]) > local_today():
        raise RuleError("Accept an actual purchase, not a future-dated expected delivery.")
    sku_versions = {}
    for entry in p["draft"]["lines"]:
        sku = inventory.product(db, entry["product_id"])
        sku_versions[sku["id"]] = sku["version"]
        inventory.convert(db, sku["id"], Decimal(1), entry["unit"], sku["unit"])
    return {
        "purchase_id": pid,
        "version": expected,
        "invoice": p["draft"],
        "sku_versions": sku_versions,
        "total_paise": calc["expected_total_paise"],
    }


def accept(db, a):
    from .app import insert_invoice

    p = get(db, a["entity_id"], True)
    if acceptance_payload(db, p["id"], a["expected_version"]) != a["payload"]:
        raise RuleError("Purchase approval no longer matches the reviewed source.")
    for pid in sorted(a["payload"]["sku_versions"]):
        sku = inventory.product(db, pid, True)
        if sku["version"] != a["payload"]["sku_versions"][pid]:
            raise RuleError("SKU mapping or conversion changed. Review again.")
    d = PurchaseDraft.model_validate(p["draft"])
    invoice = {
        "supplier": d.supplier,
        "supplier_phone": d.supplier_phone,
        "reference": d.reference,
        "date": d.date,
        "pricing_note": d.pricing_note,
        "lines": [
            {
                "name": entry.description,
                "billed": str(entry.billed_quantity),
                "unit": entry.unit,
                "price_paise": entry.effective_price_paise,
                "received": None,
                "received_unit": "unknown",
                "unit_confirmed": False,
                "note": entry.review_note,
            }
            for entry in d.lines
        ],
    }
    docs = (
        db.execute(
            select(m.purchase_documents).where(
                store.scope(m.purchase_documents), m.purchase_documents.c.purchase_id == p["id"]
            )
        )
        .mappings()
        .all()
    )
    attachment = (docs[0]["name"], docs[0]["mime"], docs[0]["data"]) if docs else None
    c = insert_invoice(invoice, attachment=attachment)
    db.execute(
        insert(m.purchase_acceptances).values(
            id=store.uid(),
            store_id=auth.current().store_id,
            purchase_id=p["id"],
            action_id=a["id"],
            version=p["version"] + 1,
            snapshot=a["payload"],
            payload_digest=a["payload_digest"],
            total_paise=a["payload"]["total_paise"],
            accepted_by=auth.current().user_id,
            accepted_at=datetime.now(timezone.utc),
        )
    )
    for i, entry in enumerate(d.lines):
        db.execute(
            insert(m.purchase_lines).values(
                id=store.uid(),
                store_id=auth.current().store_id,
                purchase_id=p["id"],
                product_id=entry.product_id,
                position=i,
                description=entry.description,
                billed_quantity=entry.billed_quantity,
                unit=entry.unit,
                unit_price_paise=entry.unit_price_paise,
                effective_price_paise=entry.effective_price_paise,
                tax_paise=entry.tax_paise,
                tax_rate=entry.tax_rate,
            )
        )
    db.execute(
        update(m.purchases)
        .where(store.scope(m.purchases), m.purchases.c.id == p["id"])
        .values(case_id=c["id"], status="accepted", version=p["version"] + 1)
    )
    store.audit_record(
        db,
        p["id"],
        "Purchase accepted; stock unchanged",
        p["version"],
        p["version"] + 1,
        source_ids=[p["id"], c["id"], a["id"]],
        snapshot=a["payload"],
        entity_type="purchase",
    )
    return view(db, get(db, p["id"]))


def create_receiving(db, pid, raw):
    auth.current("write")
    p = get(db, pid)
    body = ReceivingDraft.model_validate(raw)
    if p["status"] != "accepted" or p["delivery_complete"] or p["version"] != body.purchase_version:
        raise RuleError(
            "Receiving needs the current accepted, incomplete purchase. Reload the source."
        )
    rid = store.uid()
    db.execute(
        insert(m.receiving_drafts).values(
            id=rid,
            store_id=auth.current().store_id,
            purchase_id=pid,
            version=1,
            purchase_version=body.purchase_version,
            status="draft",
            payload=body.model_dump(mode="json"),
            created_by=auth.current().user_id,
            created_at=datetime.now(timezone.utc),
        )
    )
    store.audit_record(
        db,
        rid,
        "Physical receiving draft captured",
        new=1,
        source_ids=[pid, rid],
        entity_type="receiving",
    )
    return {
        "id": rid,
        "version": 1,
        "purchase_id": pid,
        "status": "draft",
        "payload": body.model_dump(mode="json"),
    }


def receiving(db, rid, lock=False):
    q = select(m.receiving_drafts).where(
        store.scope(m.receiving_drafts), m.receiving_drafts.c.id == rid
    )
    row = db.execute(q.with_for_update() if lock else q).mappings().first()
    if not row:
        raise KeyError(rid)
    return dict(row)


def receipt_payload(db, rid, expected):
    r = receiving(db, rid)
    p = get(db, r["purchase_id"])
    body = ReceivingDraft.model_validate(r["payload"])
    ls = lines(db, p["id"])
    if (
        r["version"] != expected
        or r["status"] != "draft"
        or p["status"] != "accepted"
        or p["delivery_complete"]
        or p["version"] != r["purchase_version"]
    ):
        raise RuleError(
            "Receiving or purchase changed. Review a new receiving draft against the current version."
        )
    if body.received_on is None or body.received_on > local_today():
        raise RuleError("Confirm the actual receiving date; it cannot be in the future.")
    if len(body.lines) != len(ls) or {entry.purchase_line_id for entry in body.lines} != {
        entry["id"] for entry in ls
    }:
        raise RuleError(
            "Receiving must cover each accepted invoice line exactly once, with unknown quantities left uncounted."
        )
    if body.delivery_complete and not body.pricing_confirmed:
        raise RuleError(
            "Final receiving requires effective-price confirmation before shortage evidence is finalized."
        )
    sku_versions = {}
    computed = []
    observed = False
    for line in ls:
        item = next(entry for entry in body.lines if entry.purchase_line_id == line["id"])
        sku = inventory.product(db, line["product_id"])
        sku_versions[sku["id"]] = {"version": sku["version"], "stock_version": sku["stock_version"]}
        if item.quantity is None:
            if body.delivery_complete:
                raise RuleError(
                    "Final delivery needs an actual count for every item in this delivery. Enter zero explicitly when none arrived."
                )
            computed.append({"purchase_line_id": line["id"], "observed": False})
            continue
        observed = True
        if not item.unit_confirmed:
            raise RuleError("Confirm the physical and billed units for each counted item.")
        if item.damaged_quantity > item.quantity:
            raise RuleError("Damaged quantity cannot exceed physically received quantity.")
        invqty, ids1 = inventory.convert(db, sku["id"], item.quantity, item.unit, line["unit"])
        good, ids2 = inventory.convert(
            db, sku["id"], item.quantity - item.damaged_quantity, item.unit, sku["unit"]
        )
        # Preserve physical overdelivery in the receipt and stock ledger. The linked
        # claim calculator flags it for review and never creates negative recovery.
        computed.append(
            {
                "purchase_line_id": line["id"],
                "observed": True,
                "invoice_quantity": inventory.quantity(invqty),
                "stock_quantity": inventory.quantity(good),
                "conversion_ids": sorted(set(ids1 + ids2)),
            }
        )
    if not observed:
        raise RuleError("Record at least one actual count before accepting a receiving.")
    c = store.get(db, p["case_id"])
    if c["approved_version"] is not None or c["resolutions"]:
        raise RuleError("Accepted claim history cannot be rewritten by receiving.")
    return {
        "receiving_id": rid,
        "receiving_version": expected,
        "purchase_id": p["id"],
        "purchase_version": p["version"],
        "case_version": c["version"],
        "input": body.model_dump(mode="json"),
        "computed": computed,
        "sku_versions": sku_versions,
    }


def accept_receiving(db, a, operation_id):
    r = receiving(db, a["entity_id"], True)
    p = get(db, r["purchase_id"], True)
    for pid in sorted(a["payload"]["sku_versions"]):
        inventory.product(db, pid, True)
    if receipt_payload(db, r["id"], a["expected_version"]) != a["payload"]:
        raise RuleError("Receiving approval is stale. Recheck purchase, counts and stock versions.")
    body = ReceivingDraft.model_validate(r["payload"])
    rid = store.uid()
    ls = lines(db, p["id"])
    db.execute(
        insert(m.receipts).values(
            id=rid,
            store_id=auth.current().store_id,
            purchase_id=p["id"],
            draft_id=r["id"],
            purchase_version=p["version"],
            delivery_complete=body.delivery_complete,
            payload=a["payload"],
            action_id=a["id"],
            operation_id=operation_id,
            accepted_by=auth.current().user_id,
            accepted_at=datetime.now(timezone.utc),
        )
    )
    events = []
    for line in ls:
        item = next(entry for entry in body.lines if entry.purchase_line_id == line["id"])
        calc = next(
            entry for entry in a["payload"]["computed"] if entry["purchase_line_id"] == line["id"]
        )
        if not calc["observed"]:
            continue
        sku = inventory.product(db, line["product_id"], True)
        lid = None
        line_id = store.uid()
        if Decimal(calc["stock_quantity"]) > 0:
            sid = inventory.source(
                db,
                sku["id"],
                "receipt",
                line_id,
                f"{p['draft']['reference'][:60]}:{rid}:{line['position']}",
                body.received_on,
                "Merchant accepted physical receiving",
                {
                    "receiving_id": rid,
                    "purchase_id": p["id"],
                    "line_id": line["id"],
                    "quantity": str(item.quantity),
                    "damaged_quantity": str(item.damaged_quantity),
                    "conversion_ids": calc["conversion_ids"],
                },
            )
            lid = inventory.make_lot(db, sku, sid, item.batch_reference, item.expiry_date)
            events.append(
                inventory.append_event(
                    db, sku, sid, "receipt", Decimal(calc["stock_quantity"]), operation_id, lid
                )
            )
        db.execute(
            insert(m.receipt_lines).values(
                id=line_id,
                store_id=auth.current().store_id,
                receipt_id=rid,
                purchase_line_id=line["id"],
                product_id=sku["id"],
                quantity=item.quantity,
                damaged_quantity=item.damaged_quantity,
                invoice_quantity=Decimal(calc["invoice_quantity"]),
                stock_quantity=Decimal(calc["stock_quantity"]),
                unit=item.unit,
                note=item.note,
                conversion_ids=calc["conversion_ids"],
                lot_id=lid,
            )
        )
    # Claims follow cumulative physical counts, never billed quantities or expected stock.
    with store.mutate(p["case_id"], a["payload"]["case_version"]) as (_, c):
        for line in ls:
            q = select(func.sum(m.receipt_lines.c.invoice_quantity)).where(
                store.scope(m.receipt_lines), m.receipt_lines.c.purchase_line_id == line["id"]
            )
            total = db.execute(q).scalar_one()
            legacy = c["invoice"]["lines"][line["position"]]
            legacy.update(
                received=inventory.quantity(total) if total is not None else None,
                received_unit=line["unit"] if total is not None else "unknown",
                unit_confirmed=total is not None,
            )
        c.update(delivery_complete=body.delivery_complete, pricing_confirmed=body.pricing_confirmed)
        audit(
            c,
            "Physical receiving accepted",
            "Cumulative merchant counts linked to purchase/receipt. Only undamaged received quantities increased stock.",
        )
    db.execute(
        update(m.receiving_drafts)
        .where(store.scope(m.receiving_drafts), m.receiving_drafts.c.id == r["id"])
        .values(status="accepted", version=r["version"] + 1)
    )
    db.execute(
        update(m.purchases)
        .where(store.scope(m.purchases), m.purchases.c.id == p["id"])
        .values(version=p["version"] + 1, delivery_complete=body.delivery_complete)
    )
    store.audit_record(
        db,
        rid,
        "Physical receiving accepted",
        p["version"],
        p["version"] + 1,
        source_ids=[p["id"], p["case_id"], r["id"]] + events,
        entity_type="receiving",
    )
    return {"receipt_id": rid, "event_ids": events, "purchase": view(db, get(db, p["id"]))}


def case_link(db, case_id):
    row = (
        db.execute(
            select(m.purchases.c.id, m.purchases.c.version).where(
                store.scope(m.purchases), m.purchases.c.case_id == case_id
            )
        )
        .mappings()
        .first()
    )
    if not row:
        return None
    ids = [
        r[0]
        for r in db.execute(
            select(m.receipts.c.id).where(
                store.scope(m.receipts), m.receipts.c.purchase_id == row["id"]
            )
        )
    ]
    event_ids = [
        r[0]
        for r in db.execute(
            select(m.inventory_events.c.id)
            .join(
                m.inventory_sources,
                (m.inventory_sources.c.id == m.inventory_events.c.source_id)
                & (m.inventory_sources.c.store_id == m.inventory_events.c.store_id),
            )
            .join(
                m.receipt_lines,
                (m.receipt_lines.c.id == m.inventory_sources.c.source_entity_id)
                & (m.receipt_lines.c.store_id == m.inventory_sources.c.store_id),
            )
            .join(
                m.receipts,
                (m.receipts.c.id == m.receipt_lines.c.receipt_id)
                & (m.receipts.c.store_id == m.receipt_lines.c.store_id),
            )
            .where(store.scope(m.inventory_events), m.receipts.c.purchase_id == row["id"])
        )
    ]
    return {
        "purchase_id": row["id"],
        "purchase_version": row["version"],
        "receipt_ids": ids,
        "inventory_event_ids": event_ids,
    }


def require_legacy_edit_allowed(db, case_id):
    if case_link(db, case_id):
        raise RuleError(
            "This case is linked to an accepted purchase. Use its receiving workflow; accepted invoice and inventory evidence cannot be overwritten here."
        )
