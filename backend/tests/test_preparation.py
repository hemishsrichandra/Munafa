from datetime import date
import uuid
from sqlalchemy import update
from backend import models as m
from backend.db import engine
from backend.tests.test_commerce import purchase
from backend.tests.test_trust import other_client


def period():
    return {"start": date.today().isoformat(), "end": date.today().isoformat()}


def propose(client, row):
    r = client.post("/api/preparation/proposals", json={**period(), "source_ids": [row["id"]]})
    assert r.status_code == 201, r.text
    return r.json()


def approve(client, a):
    r = client.post(
        f"/api/actions/{a['id']}/approve",
        json={"version": a["version"], "payload_digest": a["payload_digest"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_pack_sources_totals_approval_and_tenant(client):
    row, _ = purchase(client)
    result = client.post("/api/preparation/preview", json=period())
    assert result.status_code == 200, result.text
    pack = result.json()
    assert pack["total_recorded_paise"] == 20000
    assert pack["status"] == "needs_external_review" and pack["mode"] == "demo"
    assert pack["records"][0]["purchase_id"] == row["id"]
    assert "supplier_phone" not in result.text
    assert pack["records"][0]["exceptions"]
    a = propose(client, row)
    assert client.get("/api/preparation/export", params={"action_id": a["id"]}).status_code == 403
    a = approve(client, a)
    key = uuid.uuid4().hex
    path = f"/api/actions/{a['id']}/execute"
    body = {"version": a["version"]}
    first = client.post(path, json=body, headers={"Idempotency-Key": key})
    assert first.status_code == 200, first.text
    assert client.post(path, json=body, headers={"Idempotency-Key": key}).json() == first.json()
    downloaded = client.get(first.json()["download_url"])
    assert (
        downloaded.status_code == 200
        and downloaded.json()["approval"]["payload_digest"] == a["payload_digest"]
    )
    other, _ = other_client()
    assert other.post("/api/preparation/preview", json=period()).json()["records"] == []
    assert other.get(first.json()["download_url"]).status_code == 404
    assert (
        other.post(
            "/api/preparation/proposals", json={**period(), "source_ids": [row["id"]]}
        ).status_code
        == 409
    )


def test_stale_pack_and_edit_invalidates_approval(client):
    row, _ = purchase(client)
    a = approve(client, propose(client, row))
    with engine().begin() as db:
        db.execute(
            update(m.purchases)
            .where(m.purchases.c.id == row["id"])
            .values(version=row["version"] + 1)
        )
    r = client.post(f"/api/actions/{a['id']}/execute", json={"version": a["version"]})
    assert r.status_code == 409
    revised = client.patch(
        f"/api/actions/{a['id']}", json={"version": a["version"], "payload": {"changed": True}}
    )
    assert revised.status_code == 200 and revised.json()["approved_digest"] is None
    assert (
        client.post(
            f"/api/actions/{a['id']}/execute", json={"version": revised.json()["version"]}
        ).status_code
        == 409
    )


def test_empty_period_spoof_and_export_role(client):
    assert client.post("/api/preparation/preview", json=period()).json()["records"] == []
    assert (
        client.post("/api/preparation/preview", json={**period(), "store_id": "spoof"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/preparation/preview", json={"start": "2026-10-01", "end": "2025-01-01"}
        ).status_code
        == 422
    )
    viewer, _ = other_client("viewer")
    assert (
        viewer.post(
            "/api/preparation/proposals", json={**period(), "source_ids": ["x"]}
        ).status_code
        == 403
    )
