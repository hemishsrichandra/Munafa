"""Manual capture never calls a provider; original sources and review gates persist."""

import json
from pathlib import Path
from sqlalchemy import select, func
from backend import models as m
from backend.db import engine
from backend.providers import SarvamDocument
from backend.tests.test_commerce import draft, product


def test_manual_photo_preserves_fields_and_source_without_ai(client, monkeypatch):
    monkeypatch.setattr(
        SarvamDocument,
        "extract",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Manual capture must not call AI")),
    )
    p = product(client)
    fields = draft(p, "2.5")
    image = (
        Path(__file__).resolve().parents[2] / "evaluation/validation-v2/printed-en.png"
    ).read_bytes()
    r = client.post(
        "/api/purchases/document",
        files={"file": ("synthetic.png", image, "image/png")},
        data={"manual_draft": json.dumps(fields)},
    )
    assert r.status_code == 201, r.text
    result = r.json()
    assert result["status"] == "draft" and result["draft"]["supplier"] == fields["supplier"]
    assert result["draft"]["lines"][0]["billed_quantity"] == "2.5"
    assert result["documents"] and not result["receipts"]
    assert client.get("/api/purchase-documents/" + result["documents"][0]["id"]).content == image
    assert result["revisions"][-1]["provenance"]["provider"] is None
    duplicate = client.post(
        "/api/purchases/document",
        files={"file": ("synthetic.png", image, "image/png")},
        data={"manual_draft": json.dumps(fields)},
    )
    assert duplicate.status_code == 409
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.purchases)).scalar() == 1
        assert db.execute(select(func.count()).select_from(m.inventory_events)).scalar() == 0
        assert db.execute(select(func.count()).select_from(m.ai_runs)).scalar() == 0


def test_manual_text_and_invalid_manual_schema_never_call_ai(client, monkeypatch):
    monkeypatch.setattr(
        SarvamDocument,
        "extract",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("Manual capture must not call AI")),
    )
    fields = draft(product(client), "2.5")
    r = client.post(
        "/api/purchases/extract-text",
        json={"text": "Synthetic original handwritten transcription", "manual_draft": fields},
    )
    assert r.status_code == 201, r.text
    assert (
        client.get("/api/purchase-documents/" + r.json()["documents"][0]["id"]).content
        == b"Synthetic original handwritten transcription"
    )
    image = b"\x89PNG\r\n\x1a\nsynthetic"
    for value in ["invalid-json", json.dumps({**fields, "received_quantity": "9"})]:
        bad = client.post(
            "/api/purchases/document",
            files={"file": ("synthetic.png", image, "image/png")},
            data={"manual_draft": value},
        )
        assert bad.status_code == 422
        assert "Manual bill fields are invalid" in bad.json()["detail"]


def test_offline_manual_text_source_is_preserved_and_replayed(client):
    import uuid
    from datetime import datetime, timezone

    fields = draft(product(client), "2.5")
    operation = {
        "operation_id": str(uuid.uuid4()),
        "operation_type": "purchase_create",
        "payload_schema_version": 1,
        "client_created_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": None,
        "expected_version": None,
        "dependency_ids": [],
        "payload": {"draft": fields, "source_text": "Synthetic original offline transcription"},
    }
    first = client.post(
        "/api/sync/operations",
        json=operation,
        headers={"Idempotency-Key": operation["operation_id"]},
    )
    assert first.status_code == 201, first.text
    again = client.post(
        "/api/sync/operations",
        json=operation,
        headers={"Idempotency-Key": operation["operation_id"]},
    )
    assert again.status_code == 201 and again.json() == first.json()
    saved = client.get("/api/purchases/" + first.json()["entity_id"]).json()
    assert len(saved["documents"]) == 1
    assert (
        client.get("/api/purchase-documents/" + saved["documents"][0]["id"]).content
        == b"Synthetic original offline transcription"
    )
