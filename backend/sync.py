"""Allowlisted offline proposals. No approvals, recovery, messages or stock truth here."""

import base64
import binascii
import hashlib
from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from pydantic import Field, AwareDatetime, ValidationError
from sqlalchemy import select
from . import auth, store, models as m
from .domain import StrictModel, Invoice, Review, Quantity, audit, present, RuleError

router = APIRouter(prefix="/api/sync")


class Operation(StrictModel):
    operation_id: UUID
    operation_type: Literal[
        "invoice_create",
        "receiving_save",
        "attachment_upload",
        "purchase_create",
        "purchase_document_upload",
        "purchase_receiving_capture",
        "inventory_movement",
        "proof_upload",
    ]
    payload_schema_version: Literal[1]
    entity_id: str | None = Field(default=None, max_length=64)
    expected_version: int | None = Field(default=None, ge=0)
    client_created_at: AwareDatetime
    dependency_ids: list[UUID] = Field(default_factory=list, max_length=10)
    payload: dict


class InvoicePayload(StrictModel):
    invoice: Invoice


class Count(StrictModel):
    received: Quantity | None = Field(default=None, ge=0, le=100000)
    received_unit: Literal["pack", "piece", "carton", "kg", "unknown"]
    unit_confirmed: bool


class ReceivingPayload(StrictModel):
    lines: list[Count] = Field(min_length=1, max_length=30)
    delivery_complete: bool
    pricing_confirmed: bool
    note: str = Field(default="", max_length=500)


class AttachmentPayload(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    mime: Literal["image/png", "image/jpeg", "image/webp", "application/pdf"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_base64: str = Field(min_length=1, max_length=5592408)


def apply_operation(body: Operation, request: Request):
    from .app import insert_invoice, validate_file

    auth.current("write")
    if request.headers.get("idempotency-key") != str(body.operation_id):
        raise HTTPException(400, "Operation ID must match the Idempotency-Key.")
    with store.connect("write") as db:
        for dependency in body.dependency_ids:
            accepted = (
                db.execute(
                    select(m.operations).where(
                        store.scope(m.operations),
                        m.operations.c.actor_id == auth.current().user_id,
                        m.operations.c.operation_key == str(dependency),
                    )
                )
                .mappings()
                .first()
            )
            if not accepted or accepted["response"].get("operation_id") != str(dependency):
                raise HTTPException(409, "A prerequisite has not been accepted for this store.")
        if body.operation_type in (
            "purchase_create",
            "purchase_document_upload",
            "purchase_receiving_capture",
            "inventory_movement",
            "proof_upload",
        ):
            from .commerce_api import apply_sync

            return apply_sync(db, body)
        if body.operation_type == "invoice_create":
            if body.entity_id is not None or body.expected_version is not None:
                raise HTTPException(422, "A new invoice cannot overwrite an existing case.")
            payload = InvoicePayload.model_validate(body.payload)
            c = insert_invoice(payload.invoice.model_dump())
        else:
            if not body.entity_id or body.expected_version is None:
                raise HTTPException(422, "Entity and expected version are required.")
            from .purchasing import require_legacy_edit_allowed

            require_legacy_edit_allowed(db, body.entity_id)
            with store.mutate(body.entity_id, body.expected_version, "write") as (_, c):
                if c["status"] != "review" or c["approved_version"] is not None or c["resolutions"]:
                    raise RuleError(
                        "Only an unapproved receiving draft can sync. Accepted evidence is unchanged."
                    )
                if body.operation_type == "receiving_save":
                    payload = ReceivingPayload.model_validate(body.payload)
                    if len(payload.lines) != len(c["invoice"]["lines"]):
                        raise RuleError("Invoice items changed. Review the latest server version.")
                    invoice = c["invoice"]
                    for line, count in zip(invoice["lines"], payload.lines):
                        line.update(count.model_dump())
                    # Receiving notes are part of the reviewed invoice source, never a credit event.
                    if payload.note:
                        invoice["pricing_note"] = payload.note
                    checked = Review(
                        version=body.expected_version,
                        invoice=invoice,
                        delivery_complete=payload.delivery_complete,
                        pricing_confirmed=payload.pricing_confirmed,
                    )
                    c["invoice"] = checked.invoice.model_dump()
                    c.update(
                        delivery_complete=checked.delivery_complete,
                        pricing_confirmed=checked.pricing_confirmed,
                    )
                    audit(
                        c,
                        "Counts reviewed",
                        "Merchant receiving draft synchronized; approval still required.",
                    )
                else:
                    payload = AttachmentPayload.model_validate(body.payload)
                    try:
                        data = base64.b64decode(payload.content_base64, validate=True)
                    except (ValueError, binascii.Error):
                        raise HTTPException(
                            422, "Attachment content is incomplete or invalid."
                        ) from None
                    if (
                        len(data) > 4 * 1024 * 1024
                        or hashlib.sha256(data).hexdigest() != payload.sha256
                    ):
                        raise HTTPException(
                            422,
                            "Attachment size or checksum did not match. Keep the original and retry.",
                        )
                    validate_file(data, payload.mime, proof=True)
                    if c["attachment_id"]:
                        raise RuleError(
                            "This invoice already has an attachment. It has not been replaced."
                        )
                    c["attachment_id"] = store.add_attachment(
                        db, c["id"], payload.name, payload.mime, data
                    )
                    audit(
                        c,
                        "Invoice attachment saved",
                        "Merchant-captured attachment; not OCR or physical receiving evidence.",
                    )
            c = present(c)
        store.audit_record(
            db,
            str(body.operation_id),
            "Offline proposal accepted",
            prior=body.expected_version,
            new=c["version"],
            source_ids=[c["id"], str(body.operation_id)] + [str(d) for d in body.dependency_ids],
            entity_type="sync_operation",
            detail=f"{body.operation_type}; schema {body.payload_schema_version}",
        )
    return {
        "operation_id": str(body.operation_id),
        "entity_id": c["id"],
        "entity_version": c["version"],
        "attachment_id": c.get("attachment_id"),
        "accepted_at": datetime.now().astimezone().isoformat(),
    }


@router.post("/operations", status_code=201)
def submit_operation(body: Operation, request: Request):
    try:
        return apply_operation(body, request)
    except ValidationError as exc:
        detail = "; ".join(".".join(map(str, e["loc"])) + ": " + e["msg"] for e in exc.errors())
        raise HTTPException(422, detail) from None
