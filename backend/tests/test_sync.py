import base64
import hashlib
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from backend import models as m
from backend.db import engine
from backend.samples import sample_invoice
from backend.tests.test_trust import other_client
from backend.tests.test_workflow import shared


def operation(kind="invoice_create", payload=None, entity=None, version=None, dependencies=None):
    return {
        "operation_id": str(uuid.uuid4()),
        "operation_type": kind,
        "payload_schema_version": 1,
        "entity_id": entity,
        "expected_version": version,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "dependency_ids": dependencies or [],
        "payload": payload if payload is not None else {"invoice": sample_invoice()},
    }


def send(client, body):
    return client.post(
        "/api/sync/operations", json=body, headers={"Idempotency-Key": body["operation_id"]}
    )


def test_sync_retry_returns_original_receipt_and_one_case_event(client):
    body = operation()
    first, retry = send(client, body), send(client, body)
    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    assert retry.headers["Idempotency-Replayed"] == "true"
    cases = client.get("/api/cases").json()
    assert len(cases) == 1 and len(cases[0]["history"]) == 1
    with engine().connect() as db:
        assert (
            db.execute(
                select(func.count())
                .select_from(m.audit_events)
                .where(
                    m.audit_events.c.entity_type == "sync_operation",
                    m.audit_events.c.entity_id == body["operation_id"],
                )
            ).scalar_one()
            == 1
        )
    changed = {**body, "payload": {"invoice": {**sample_invoice(), "reference": "changed"}}}
    assert send(client, changed).status_code == 409


def test_receiving_sync_is_versioned_and_never_an_approval_or_recovery(client):
    c = client.post("/api/invoices/sample").json()
    payload = {
        "lines": [
            {"received": 10, "received_unit": "pack", "unit_confirmed": True},
            {"received": 6, "received_unit": "pack", "unit_confirmed": True},
            {"received": 24, "received_unit": "piece", "unit_confirmed": True},
        ],
        "delivery_complete": True,
        "pricing_confirmed": True,
        "note": "Counted by merchant",
    }
    body = operation("receiving_save", payload, c["id"], c["version"])
    response = send(client, body)
    assert response.status_code == 201, response.text
    assert response.json()["entity_version"] == c["version"] + 1
    assert send(client, {**body, "operation_id": str(uuid.uuid4())}).status_code == 409
    latest = client.get("/api/cases/" + c["id"]).json()
    assert latest["status"] == "review" and latest["approved_version"] is None
    assert latest["recovered_paise"] == 0 and len(latest["history"]) == 2
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.financial_events)).scalar_one() == 0


def test_attachment_dependency_checksum_partial_failure_and_duplicate_retry(client):
    parent = operation()
    accepted = send(client, parent).json()
    raw = b"%PDF-1.4\nSynthetic offline invoice"
    payload = {
        "name": "synthetic.pdf",
        "mime": "application/pdf",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content_base64": base64.b64encode(raw).decode(),
    }
    body = operation(
        "attachment_upload", payload, accepted["entity_id"], 1, [parent["operation_id"]]
    )
    bad = {**body, "payload": {**payload, "content_base64": "incomplete"}}
    assert send(client, bad).status_code == 422
    first = send(client, body)
    assert first.status_code == 201, first.text
    assert send(client, body).json() == first.json()
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.attachments)).scalar_one() == 1
    latest = client.get("/api/cases/" + accepted["entity_id"]).json()
    assert latest["attachment_id"] == first.json()["attachment_id"] and latest["version"] == 2
    missing = operation("attachment_upload", payload, accepted["entity_id"], 2, [str(uuid.uuid4())])
    assert send(client, missing).status_code == 409


def test_sync_rejects_tenant_spoof_foreign_entity_unapproved_type_and_role(client):
    c = client.post("/api/invoices/sample").json()
    other, _ = other_client()
    payload = {"lines": [], "delivery_complete": False, "pricing_confirmed": False}
    assert send(other, operation("receiving_save", payload, c["id"], 1)).status_code == 404
    assert send(client, {**operation(), "store_id": "forged"}).status_code == 422
    assert send(client, {**operation(), "operation_type": "approve_case"}).status_code == 422
    viewer, _ = other_client("viewer")
    assert send(viewer, operation()).status_code == 403
    bad = operation()
    bad["payload"]["invoice"]["lines"][0]["billed"] = 1.25
    assert send(client, bad).status_code == 422
    mismatch = client.post("/api/sync/operations", json=operation())
    assert mismatch.status_code == 400


def test_offline_operations_cannot_modify_approved_financial_history(client):
    c = shared(client)
    body = operation(
        "receiving_save",
        {"lines": [], "delivery_complete": False, "pricing_confirmed": False},
        c["id"],
        c["version"],
    )
    assert send(client, body).status_code == 409
    assert client.get("/api/cases/" + c["id"]).json() == c
