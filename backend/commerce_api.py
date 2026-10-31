"""Authenticated purchase/catalog/receiving routes; approval execution stays server-side."""

from datetime import timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select
from . import store, auth, actions, inventory, purchasing, models as m
from .commerce_models import (
    ProductInput,
    ConversionInput,
    PurchaseDraft,
    ReceivingDraft,
    MovementInput,
)
from .domain import StrictModel, RuleError, local_today

router = APIRouter(prefix="/api")


class DraftEdit(StrictModel):
    version: int = Field(ge=1, strict=True)
    draft: PurchaseDraft


class ProductEdit(StrictModel):
    version: int = Field(ge=1, strict=True)
    product: ProductInput


class TextSource(StrictModel):
    text: str = Field(min_length=1, max_length=18000)
    manual_draft: PurchaseDraft | None = None


class Proposal(StrictModel):
    action_type: str
    entity_id: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=0, strict=True)
    payload: dict = Field(default_factory=dict)


class ReceiptProposal(StrictModel):
    version: int = Field(ge=1, strict=True)
    payload: ReceivingDraft


def action_payload(db, kind, eid, expected, payload):
    if kind == "accept_purchase":
        return purchasing.acceptance_payload(db, eid, expected)
    if kind == "accept_receiving":
        return purchasing.receipt_payload(db, eid, expected)
    if kind == "inventory_movement":
        body = MovementInput.model_validate(payload)
        if body.product_id != eid or body.expected_stock_version != expected:
            raise RuleError("Stock proposal must bind the selected SKU and exact source version.")
        return inventory.movement_payload(db, body.model_dump(mode="json"))
    raise RuleError("Unsupported commerce action.")


def execute(db, a, key):
    if a["action_type"] == "accept_purchase":
        result = purchasing.accept(db, a)
    elif a["action_type"] == "accept_receiving":
        result = purchasing.accept_receiving(db, a, key)
    elif a["action_type"] == "inventory_movement":
        result = inventory.execute_movement(db, a["payload"], key)
    else:
        raise RuleError("Unsupported commerce action.")
    actions.executed(db, a)
    return result


@router.post("/commerce/proposals", status_code=201)
def propose(body: Proposal, request: Request):
    if body.action_type not in ("accept_purchase", "accept_receiving", "inventory_movement"):
        raise RuleError("This endpoint accepts purchase/receiving/stock proposals only.")
    with store.connect("write") as db:
        return actions.propose(
            db,
            body.action_type,
            body.entity_id,
            body.payload,
            body.expected_version,
            request.headers["idempotency-key"],
        )


@router.get("/products")
def products():
    with store.connect() as db:
        return inventory.products(db)


@router.post("/products", status_code=201)
def create_product(body: ProductInput):
    with store.connect("write") as db:
        return inventory.create_product(db, body)


@router.patch("/products/{pid}")
def edit_product(pid: str, body: ProductEdit):
    with store.connect("write") as db:
        return inventory.change_product(db, pid, body.version, body.product)


@router.get("/products/{pid}/movements")
def movements(pid: str):
    with store.connect() as db:
        return inventory.movements(db, pid)


@router.get("/products/{pid}/conversions")
def conversions(pid: str):
    with store.connect() as db:
        inventory.product(db, pid)
        return [
            {
                **r,
                "factor": inventory.quantity(r["factor"]),
                "created_at": r["created_at"].isoformat(),
            }
            for r in db.execute(
                select(m.conversions).where(
                    store.scope(m.conversions), m.conversions.c.product_id == pid
                )
            ).mappings()
        ]


@router.post("/products/{pid}/conversions", status_code=201)
def add_conversion(pid: str, body: ConversionInput):
    with store.connect("approve") as db:
        return inventory.add_conversion(db, pid, body)


@router.get("/inventory/expiry")
def expiry():
    with store.connect() as db:
        today = local_today()
        store_name = auth.current().store_name
        result = []
        for p in inventory.products(db):
            last_line = (
                db.execute(
                    select(
                        m.purchase_lines.c.effective_price_paise,
                        m.purchase_lines.c.unit_price_paise,
                    )
                    .join(
                        m.purchases,
                        (m.purchase_lines.c.purchase_id == m.purchases.c.id)
                        & (m.purchase_lines.c.store_id == m.purchases.c.store_id),
                    )
                    .where(
                        store.scope(m.purchase_lines),
                        store.scope(m.purchases),
                        m.purchase_lines.c.product_id == p["id"],
                        m.purchases.c.status == "accepted",
                    )
                    .order_by(m.purchases.c.created_at.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )

            unit_cost = (
                last_line["effective_price_paise"] or last_line["unit_price_paise"]
                if last_line
                else None
            )

            for lot in inventory.lots(db, p["id"]):
                if (
                    lot["expiry_date"] is not None
                    and date.fromisoformat(lot["expiry_date"]) <= today + timedelta(days=30)
                    and Decimal(lot["quantity"]) > 0
                ):
                    exp_date = date.fromisoformat(lot["expiry_date"])
                    days_until = (exp_date - today).days
                    is_expired = days_until < 0

                    if is_expired:
                        urgency = "expired"
                        action = "Remove from shelf immediately / Request supplier return/credit"
                        discount_pct = 0
                    elif days_until <= 7:
                        urgency = "critical"
                        action = "Immediate clearance: 40-50% off flash discount"
                        discount_pct = 50
                    elif days_until <= 15:
                        urgency = "warning"
                        action = "Promote near counter / 20-30% off combo deal"
                        discount_pct = 25
                    else:
                        urgency = "moderate"
                        action = "Feature in customer broadcast / first-out display"
                        discount_pct = 10

                    qty = Decimal(lot["quantity"])
                    loss_risk_paise = (
                        int(
                            (qty * Decimal(unit_cost)).quantize(
                                Decimal("1"), rounding=ROUND_HALF_UP
                            )
                        )
                        if unit_cost is not None
                        else None
                    )
                    clearance_price_paise = (
                        int(
                            (
                                Decimal(unit_cost) * Decimal(100 - discount_pct) / Decimal(100)
                            ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                        )
                        if unit_cost is not None and discount_pct > 0
                        else None
                    )

                    clearance_rupees_str = (
                        f"₹{clearance_price_paise // 100}.{clearance_price_paise % 100:02d}"
                        if clearance_price_paise is not None
                        else "special discount"
                    )
                    draft_msg = (
                        f"Offer from {store_name}: Batch of {p['name']} available at a {discount_pct}% clearance discount "
                        f"({clearance_rupees_str} per {p['unit']})! Limited stock of {lot['quantity']} {p['unit']} left. "
                        f"Valid until {lot['expiry_date']}."
                        if not is_expired
                        else f"Alert for {store_name}: Batch {lot.get('batch_reference') or 'unreferenced'} of {p['name']} "
                        f"expired on {lot['expiry_date']}. Remove from sale."
                    )

                    result.append(
                        {
                            "product_id": p["id"],
                            "product_name": p["name"],
                            "unit": p["unit"],
                            **lot,
                            "expired": is_expired,
                            "days_until_expiry": days_until,
                            "urgency": urgency,
                            "unit_cost_paise": unit_cost,
                            "loss_risk_paise": loss_risk_paise,
                            "suggested_action": action,
                            "suggested_discount_percent": discount_pct,
                            "suggested_clearance_price_paise": clearance_price_paise,
                            "whatsapp_liquidation_draft": draft_msg,
                        }
                    )

        result.sort(key=lambda x: (0 if x["expired"] else 1, x["days_until_expiry"]))
        total_loss = sum(
            lot_item["loss_risk_paise"] for lot_item in result if lot_item["loss_risk_paise"]
        )
        expired_count = sum(1 for lot_item in result if lot_item["expired"])
        expiring_count = sum(1 for lot_item in result if not lot_item["expired"])
        critical_count = sum(
            1 for lot_item in result if lot_item["urgency"] in ("expired", "critical")
        )

        return {
            "as_of": today.isoformat(),
            "window_days": 30,
            "total_lots": len(result),
            "total_expired_count": expired_count,
            "total_expiring_soon_count": expiring_count,
            "critical_lots_count": critical_count,
            "total_loss_risk_paise": total_loss,
            "lots": result,
        }


@router.get("/inventory/reorder-suggestions")
def reorder_suggestions():
    import urllib.parse
    import re

    with store.connect() as db:
        prods = inventory.products(db)
        store_name = auth.current().store_name
        suggestions = []

        for p in prods:
            if not p.get("below_threshold") or p.get("reorder_threshold") is None:
                continue

            stock_qty = Decimal(p["stock_quantity"])
            threshold_qty = Decimal(p["reorder_threshold"])

            last_line_query = (
                select(
                    m.purchase_lines.c.effective_price_paise,
                    m.purchase_lines.c.billed_quantity,
                    m.purchase_lines.c.unit,
                    m.purchases.c.draft,
                    m.purchases.c.created_at,
                )
                .join(
                    m.purchases,
                    (m.purchase_lines.c.purchase_id == m.purchases.c.id)
                    & (m.purchase_lines.c.store_id == m.purchases.c.store_id),
                )
                .where(
                    store.scope(m.purchase_lines),
                    store.scope(m.purchases),
                    m.purchase_lines.c.product_id == p["id"],
                    m.purchases.c.status == "accepted",
                )
                .order_by(m.purchases.c.created_at.desc())
                .limit(1)
            )
            last_line = db.execute(last_line_query).mappings().first()

            last_price = last_line["effective_price_paise"] if last_line else None
            last_billed_qty = Decimal(last_line["billed_quantity"]) if last_line else None
            supplier_name = (
                last_line["draft"].get("supplier")
                if last_line and isinstance(last_line["draft"], dict)
                else None
            ) or "Preferred Supplier"
            supplier_phone = (
                last_line["draft"].get("supplier_phone")
                if last_line and isinstance(last_line["draft"], dict)
                else ""
            ) or ""
            last_billed_date = (
                last_line["draft"].get("date")
                if last_line and isinstance(last_line["draft"], dict)
                else None
            )

            needed = (threshold_qty * 2) - stock_qty
            if last_billed_qty and last_billed_qty >= needed:
                reorder_qty = last_billed_qty
            else:
                reorder_qty = max(needed, threshold_qty)
            if reorder_qty <= 0:
                reorder_qty = threshold_qty

            reorder_qty_str = inventory.quantity(reorder_qty)
            est_cost_paise = int(round(reorder_qty * last_price)) if last_price else None

            po_message = (
                f"Order from {store_name}: Please send {reorder_qty_str} {p['unit']} of "
                f"{p['name']}. Standard payment upon delivery. Thank you!"
            )

            clean_phone = re.sub(r"\D", "", supplier_phone)
            encoded_msg = urllib.parse.quote(po_message)
            whatsapp_url = (
                f"https://wa.me/{clean_phone}?text={encoded_msg}"
                if clean_phone
                else f"https://wa.me/?text={encoded_msg}"
            )

            suggestions.append(
                {
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "code": p["code"],
                    "unit": p["unit"],
                    "stock_quantity": p["stock_quantity"],
                    "reorder_threshold": p["reorder_threshold"],
                    "recommended_reorder_qty": reorder_qty_str,
                    "last_price_paise": last_price,
                    "estimated_cost_paise": est_cost_paise,
                    "preferred_supplier": supplier_name,
                    "supplier_phone": supplier_phone,
                    "last_billed_date": last_billed_date,
                    "po_message": po_message,
                    "whatsapp_url": whatsapp_url,
                }
            )

        return {"count": len(suggestions), "suggestions": suggestions}


@router.get("/purchases")
def purchases():
    with store.connect() as db:
        rows = db.execute(
            select(m.purchases)
            .where(store.scope(m.purchases))
            .order_by(m.purchases.c.created_at.desc())
            .limit(100)
        ).mappings()
        return [purchasing.view(db, dict(r)) for r in rows]


@router.get("/purchases/{pid}")
def get_purchase(pid: str):
    with store.connect() as db:
        return purchasing.view(db, purchasing.get(db, pid))


@router.post("/purchases/manual", status_code=201)
def manual(body: PurchaseDraft):
    with store.connect("write") as db:
        return purchasing.create(db, body.model_dump(mode="json"))


@router.post("/purchases/sample", status_code=201)
def sample():
    if not auth.current("write").demo:
        raise HTTPException(403, "Samples require an isolated demo store.")
    draft = {
        "supplier": "Synthetic Kirana Wholesale",
        "reference": "KIRANA-DEMO-1",
        "date": local_today().isoformat(),
        "lines": [
            {
                "description": "Rice",
                "sku_candidate": "Rice",
                "billed_quantity": "2.5",
                "unit": "kg",
                "unit_price_paise": 8000,
                "effective_price_paise": 8000,
            }
        ],
        "subtotal_paise": 20000,
        "tax_paise": 0,
        "discount_paise": 0,
        "total_paise": 20000,
        "pricing_note": "Synthetic sample; merchant must select its SKU and review all fields.",
    }
    with store.connect("write") as db:
        return purchasing.create(
            db,
            draft,
            "sample",
            provenance={"source": "synthetic_sample", "provider": None, "review_required": True},
        )


@router.patch("/purchases/{pid}")
def edit_purchase(pid: str, body: DraftEdit):
    with store.connect("write") as db:
        return purchasing.revise(db, pid, body.version, body.draft.model_dump(mode="json"))


@router.post("/purchases/extract-text", status_code=201)
def from_text(body: TextSource):
    from .providers import SarvamDocument

    if body.manual_draft is not None:
        draft = body.manual_draft.model_dump(mode="json")
        prov = {"provider": None, "source": "merchant_manual_text", "review_required": True}
    else:
        draft, prov = SarvamDocument().extract(text=body.text)
    with store.connect("write") as db:
        return purchasing.create(
            db, draft, "text", ("pasted-invoice.txt", "text/plain", body.text.encode()), prov
        )


@router.post("/purchases/document", status_code=201)
async def from_document(
    file: UploadFile = File(...), manual_draft: str | None = Form(None, max_length=64000)
):
    from .app import read_file
    from starlette.concurrency import run_in_threadpool

    data, mime = await read_file(file, proof=True)
    from .providers import SarvamDocument

    if manual_draft is not None:
        from pydantic import ValidationError

        try:
            draft = PurchaseDraft.model_validate_json(manual_draft).model_dump(mode="json")
        except ValidationError:
            raise HTTPException(
                422, "Manual bill fields are invalid. Review the draft; nothing was saved."
            ) from None
        prov = {"provider": None, "source": "merchant_manual_document", "review_required": True}
    else:
        draft, prov = await run_in_threadpool(SarvamDocument().extract, data=data, mime=mime)
    with store.connect("write") as db:
        return purchasing.create(
            db, draft, "document", (file.filename or "invoice", mime, data), prov
        )


@router.get("/purchase-documents/{did}")
def get_document(did: str):
    with store.connect() as db:
        row = (
            db.execute(
                select(m.purchase_documents).where(
                    store.scope(m.purchase_documents), m.purchase_documents.c.id == did
                )
            )
            .mappings()
            .first()
        )
        if not row:
            raise KeyError(did)
        return Response(
            row["data"],
            media_type=row["mime"],
            headers={
                "Content-Disposition": 'attachment; filename="original-invoice"',
                "Cache-Control": "no-store",
            },
        )


@router.post("/purchases/{pid}/receivings", status_code=201)
def capture_receiving(pid: str, body: ReceivingDraft):
    with store.connect("write") as db:
        return purchasing.create_receiving(db, pid, body.model_dump(mode="json"))


@router.patch("/receivings/{rid}")
def edit_receiving(rid: str, body: ReceiptProposal):
    with store.connect("write") as db:
        r = purchasing.receiving(db, rid, True)
        if r["version"] != body.version or r["status"] != "draft":
            raise RuleError("Receiving is stale or already accepted.")
        purchasing.get(db, r["purchase_id"])
        from sqlalchemy import update

        db.execute(
            update(m.receiving_drafts)
            .where(store.scope(m.receiving_drafts), m.receiving_drafts.c.id == rid)
            .values(
                version=body.version + 1,
                payload=body.payload.model_dump(mode="json"),
                purchase_version=body.payload.purchase_version,
            )
        )
        store.audit_record(
            db,
            rid,
            "Receiving draft revised",
            body.version,
            body.version + 1,
            entity_type="receiving",
        )
        return {
            **r,
            "version": body.version + 1,
            "payload": body.payload.model_dump(mode="json"),
            "purchase_version": body.payload.purchase_version,
        }


class ExpectedDocument(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    name: str = Field(min_length=1, max_length=120)
    mime: str = Field(min_length=1, max_length=80)


class OfflinePurchase(StrictModel):
    draft: PurchaseDraft
    source_text: str | None = Field(default=None, min_length=1, max_length=18000)
    document: ExpectedDocument | None = None


class ConfirmedMovement(StrictModel):
    movement: MovementInput
    merchant_confirmed: bool


def apply_sync(db, body):
    """Same request transaction and idempotency receipt as the established outbox."""
    import base64
    import binascii
    import hashlib
    from datetime import datetime, timezone
    from sqlalchemy import insert, update
    from .sync import AttachmentPayload
    from .app import validate_file

    kind = body.operation_type
    attachment_id = None
    if kind == "purchase_create":
        payload = OfflinePurchase.model_validate(body.payload)
        if body.entity_id is not None or body.expected_version is not None:
            raise RuleError("New purchase draft cannot overwrite a server entity.")
        result = purchasing.create(
            db,
            payload.draft.model_dump(mode="json"),
            "offline_manual",
            document=("pasted-invoice.txt", "text/plain", payload.source_text.encode())
            if payload.source_text
            else None,
            provenance={
                "source": "offline_manual",
                "expected_document": payload.document.model_dump() if payload.document else None,
                "review_required": True,
            },
        )
        eid = result["id"]
        version = result["version"]
        family = "purchase"
    elif kind == "purchase_receiving_capture":
        payload = ReceivingDraft.model_validate(body.payload)
        if body.entity_id is None or body.expected_version != payload.purchase_version:
            raise RuleError("Receiving draft must bind the current accepted purchase version.")
        result = purchasing.create_receiving(db, body.entity_id, payload.model_dump(mode="json"))
        eid = result["id"]
        version = result["version"]
        family = "receiving_draft"
    elif kind == "inventory_movement":
        payload = ConfirmedMovement.model_validate(body.payload)
        auth.current("approve")
        if not payload.merchant_confirmed:
            raise RuleError("Explicit merchant approval of this stock event is required.")
        movement = payload.movement
        if (
            movement.product_id != body.entity_id
            or movement.expected_stock_version != body.expected_version
        ):
            raise RuleError(
                "Stock operation must match the exact SKU/version reviewed on the device."
            )
        a = actions.propose(
            db,
            "inventory_movement",
            body.entity_id,
            movement.model_dump(mode="json"),
            body.expected_version,
            str(body.operation_id),
        )
        a = actions.approve(db, a["id"], a["version"], a["payload_digest"])
        a = actions.consume(db, a["id"], a["version"])
        result = execute(db, a, str(body.operation_id))
        eid = movement.product_id
        version = result["product"]["stock_version"]
        family = "inventory_event"
    else:
        payload = AttachmentPayload.model_validate(body.payload)
        try:
            data = base64.b64decode(payload.content_base64, validate=True)
        except (ValueError, binascii.Error):
            raise HTTPException(
                422, "Incomplete attachment. Keep its original and retry."
            ) from None
        if len(data) > 4 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != payload.sha256:
            raise HTTPException(422, "Attachment size/checksum did not match.")
        validate_file(data, payload.mime, proof=True)
        if not body.entity_id or body.expected_version is None:
            raise RuleError("Attachment must bind its source entity/version.")
        if kind == "purchase_document_upload":
            p = purchasing.get(db, body.entity_id, True)
            if p["status"] != "draft" or p["version"] != body.expected_version:
                raise RuleError(
                    "Purchase changed or was accepted; original evidence has not been replaced."
                )
            did = store.uid()
            attachment_id = did
            db.execute(
                insert(m.purchase_documents).values(
                    id=did,
                    store_id=auth.current().store_id,
                    purchase_id=p["id"],
                    name=payload.name,
                    mime=payload.mime,
                    data=data,
                    sha256=payload.sha256,
                    created_at=datetime.now(timezone.utc),
                )
            )
            p["version"] += 1
            db.execute(
                update(m.purchases)
                .where(store.scope(m.purchases), m.purchases.c.id == p["id"])
                .values(version=p["version"])
            )
            purchasing.revision(
                db,
                p,
                p["draft"],
                {
                    "source": "offline_document_upload",
                    "document_id": did,
                    "document_sha256": payload.sha256,
                },
            )
            eid = p["id"]
            version = p["version"]
            family = "purchase_document"
        elif kind == "proof_upload":
            c = store.get(db, body.entity_id, True)
            if c["version"] != body.expected_version or c["status"] not in (
                "sent",
                "promised",
                "partial",
            ):
                raise RuleError(
                    "Proof upload needs the current shared/unresolved claim. No recovery is inferred from an upload."
                )
            attachment_id = store.add_attachment(db, c["id"], payload.name, payload.mime, data)
            eid = c["id"]
            version = c["version"]
            family = "proof_attachment"
        else:
            raise RuleError("Unsupported sync operation.")
    store.audit_record(
        db,
        str(body.operation_id),
        "Offline proposal accepted",
        prior=body.expected_version,
        new=version,
        source_ids=[eid, str(body.operation_id)] + ([attachment_id] if attachment_id else []),
        entity_type="sync_operation",
        detail=kind,
    )
    return {
        "operation_id": str(body.operation_id),
        "entity_id": eid,
        "entity_version": version,
        "attachment_id": attachment_id,
        "entity_family": family,
        "accepted_at": datetime.now(timezone.utc).isoformat(),
    }
