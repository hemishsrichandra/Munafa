import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from alembic import command
from alembic.config import Config
from backend import auth, models as m
from backend.app import app
from backend.db import engine
from backend.domain import Line
from pydantic import ValidationError


def other_client(role="owner", store_id=None, demo=True):
    name = uuid.uuid4().hex
    _, sid = auth.provision(name, "long-test-password", name, demo, role, store_id)
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": name, "password": "long-test-password"})
    assert r.status_code == 200, r.text
    c.headers.update({"X-CSRF-Token": r.json()["csrf"], "Idempotency-Key": uuid.uuid4().hex})
    return c, sid


def test_auth_csrf_roles_and_no_tenant_body(client):
    outsider = TestClient(app)
    assert outsider.get("/api/cases").status_code == 401
    assert client.post("/api/invoices/sample", headers={"X-CSRF-Token": ""}).status_code == 403
    assert client.post("/api/invoices/manual", json={"store_id": "spoof"}).status_code == 422
    viewer, _ = other_client("viewer")
    assert viewer.get("/api/cases").json() == []
    assert viewer.post("/api/invoices/sample").status_code == 403
    assert viewer.get("/api/export?action_id=missing").status_code == 403


def test_cross_store_entity_families(client):
    c = client.post("/api/invoices/sample").json()
    cid = c["id"]
    proof = client.post(
        f"/api/cases/{cid}/proof",
        files={"file": ("proof.pdf", b"%PDF-1.4\nTest synthetic proof", "application/pdf")},
    ).json()
    action = client.post(
        "/api/actions",
        json={"action_type": "approve_case", "entity_id": cid, "expected_version": 1},
    ).json()
    other, _ = other_client()
    assert other.get("/api/cases").json() == []
    for path in (
        f"/api/cases/{cid}",
        f"/api/attachments/{proof['attachment_id']}",
        f"/api/cases/{cid}/approvals/1",
        f"/api/actions/{action['id']}",
    ):
        assert other.get(path).status_code == 404, path
    assert other.post(f"/api/cases/{cid}/approve", json={"version": 1}).status_code == 404
    assert (
        other.post(
            f"/api/actions/{action['id']}/approve",
            json={"version": 1, "payload_digest": action["payload_digest"]},
            headers={"Idempotency-Key": uuid.uuid4().hex},
        ).status_code
        == 404
    )
    # Supplier/invoice/line/financial/history rows have no unscoped public endpoints.
    assert (
        other.get("/api/auth/me").json()["store"]["id"]
        != client.get("/api/auth/me").json()["store"]["id"]
    )


def test_idempotency_same_payload_replays_different_payload_conflicts(client):
    headers = {"Idempotency-Key": "same-operation"}
    a = client.post("/api/invoices/sample", headers=headers)
    b = client.post("/api/invoices/sample", headers=headers)
    assert a.status_code == b.status_code == 201
    assert a.json() == b.json()
    assert b.headers["Idempotency-Replayed"] == "true"
    assert len(client.get("/api/cases").json()) == 1
    bad = client.post("/api/actions", json={"action_type": "export_ledger"}, headers=headers)
    assert bad.status_code == 409


def test_approval_digest_revision_and_expiry(client):
    a = client.post("/api/actions", json={"action_type": "export_ledger"}).json()
    assert (
        client.post(
            f"/api/actions/{a['id']}/approve", json={"version": 1, "payload_digest": "bad"}
        ).status_code
        == 409
    )
    approved = client.post(
        f"/api/actions/{a['id']}/approve",
        json={"version": 1, "payload_digest": a["payload_digest"]},
    ).json()
    revised = client.patch(
        f"/api/actions/{a['id']}",
        json={"version": approved["version"], "payload": {"scope": "changed"}},
    ).json()
    assert revised["status"] == "proposed" and revised["approved_by"] is None
    assert (
        client.post(
            f"/api/actions/{a['id']}/execute", json={"version": approved["version"]}
        ).status_code
        == 409
    )
    assert client.get("/api/export?action_id=" + a["id"]).status_code == 403
    with engine().begin() as db:
        db.execute(
            update(m.actions)
            .where(m.actions.c.id == a["id"])
            .values(
                expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                - __import__("datetime").timedelta(seconds=1)
            )
        )
    assert (
        client.post(
            f"/api/actions/{a['id']}/approve",
            json={"version": revised["version"], "payload_digest": revised["payload_digest"]},
        ).status_code
        == 409
    )


def test_exact_fractional_quantity_and_schema_types(client):
    line = Line(
        name="Rice",
        billed="1.250000",
        received="0.750000",
        unit="kg",
        received_unit="kg",
        unit_confirmed=True,
        price_paise=123,
    )
    from backend.domain import calculate

    assert calculate([line], True, True)["amount_paise"] == 62  # 61.5 paise, HALF_UP per line
    for value in ("1.1234567", "NaN", 1.2, True):
        with pytest.raises((ValidationError, ValueError)):
            Line(name="Rice", billed=value, price_paise=100)
    with engine().connect() as db:
        money = db.execute(
            text(
                "SELECT data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='resolutions' AND column_name='amount_paise'"
            )
        ).scalar_one()
        assert money == "bigint"
    assert m.invoice_lines.c.billed.type.scale == 6


def test_append_only_audit_and_transaction_rollback(client):
    client.post("/api/invoices/sample")
    with pytest.raises(DBAPIError):
        with engine().begin() as db:
            db.execute(text("UPDATE audit_events SET action='tampered'"))
    with engine().connect() as db:
        before = db.execute(select(m.cases.c.id)).all()
    with pytest.raises(RuntimeError):
        with engine().begin() as db:
            db.execute(update(m.cases).values(version=999))
            raise RuntimeError("intentional transaction rollback")
    with engine().connect() as db:
        assert db.execute(select(m.cases.c.version)).scalar_one() == 1
        assert db.execute(select(m.cases.c.id)).all() == before


def test_migration_down_up_on_empty_disposable_schema(database):
    # Fixture creates a fresh schema only; there are no merchant records to discard.
    with engine().connect() as db:
        assert db.execute(select(m.cases.c.id)).first() is None
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.check(config)
    with engine().connect() as db:
        assert db.execute(select(m.cases.c.id)).first() is None


def test_production_dev_login_is_impossible(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_DEV_LOGIN", "1")
    with pytest.raises(RuntimeError):
        auth.development_login()


def test_live_store_cannot_load_synthetic_invoice(client):
    live, _ = other_client(demo=False)
    assert live.post("/api/invoices/sample").status_code == 403


def test_staff_can_review_but_cannot_approve_or_message(client):
    cid = client.post("/api/invoices/sample").json()["id"]
    sid = client.get("/api/auth/me").json()["store"]["id"]
    staff, _ = other_client("staff", sid)
    assert staff.get("/api/cases/" + cid).status_code == 200
    assert staff.post(f"/api/cases/{cid}/approve", json={"version": 1}).status_code == 403
    assert (
        staff.post(
            f"/api/cases/{cid}/message",
            json={"language": "en-IN"},
            headers={"Idempotency-Key": uuid.uuid4().hex},
        ).status_code
        == 403
    )


def test_native_bearer_is_memory_session_and_logout_revokes(client):
    native = TestClient(app)
    response = native.post(
        "/api/auth/login",
        json={"username": "test-owner", "password": "test-password-long"},
        headers={"X-Client-Platform": "android"},
    )
    assert response.status_code == 200
    token = response.json()["session_token"]
    native.cookies.clear()
    native.headers.update({"Authorization": "Bearer " + token, "Idempotency-Key": uuid.uuid4().hex})
    assert native.get("/api/cases").status_code == 200
    assert native.post("/api/invoices/sample").status_code == 201
    assert native.post("/api/auth/logout").status_code == 200
    assert native.get("/api/cases").status_code == 401


def test_concurrent_identical_operations_accept_once(client):
    from concurrent.futures import ThreadPoolExecutor

    cookies = dict(client.cookies)

    def create():
        with TestClient(app) as worker:
            worker.cookies.update(cookies)
            return worker.post(
                "/api/invoices/sample",
                headers={
                    "X-CSRF-Token": cookies["pbp_csrf"],
                    "Idempotency-Key": "concurrent-operation",
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json()["id"] == results[1].json()["id"]
    assert len(client.get("/api/cases").json()) == 1


def test_same_operation_key_in_two_stores_does_not_leak(client):
    first = client.post("/api/invoices/sample", headers={"Idempotency-Key": "shared-key"}).json()
    other, _ = other_client()
    second = other.post("/api/invoices/sample", headers={"Idempotency-Key": "shared-key"}).json()
    assert first["id"] != second["id"]
    assert other.get("/api/cases/" + first["id"]).status_code == 404


def test_export_approval_binds_ledger_versions(client):
    a = client.post("/api/actions", json={"action_type": "export_ledger"}).json()
    approved = client.post(
        f"/api/actions/{a['id']}/approve",
        json={"version": a["version"], "payload_digest": a["payload_digest"]},
    ).json()
    assert client.post("/api/invoices/sample").status_code == 201
    response = client.post(f"/api/actions/{a['id']}/execute", json={"version": approved["version"]})
    assert response.status_code == 409


def test_fractional_workflow_message_and_invoice_identity_snapshot(client):
    c = client.post("/api/invoices/sample").json()
    invoice = c["invoice"]
    invoice["lines"] = [
        {
            "name": "Rice",
            "billed": "1.250000",
            "received": "0.750000",
            "unit": "kg",
            "received_unit": "kg",
            "unit_confirmed": True,
            "price_paise": 123,
        }
    ]
    response = client.patch(
        f"/api/cases/{c['id']}/review",
        json={
            "version": c["version"],
            "invoice": invoice,
            "delivery_complete": True,
            "pricing_confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    c = response.json()
    approved = client.post(f"/api/cases/{c['id']}/approve", json={"version": c["version"]})
    assert approved.status_code == 200, approved.text
    assert approved.json()["approved_amount_paise"] == 62
    message = client.post(f"/api/cases/{c['id']}/message", json={"language": "en-IN"})
    assert message.status_code == 200, message.text
    assert "INR 0.62" in message.json()["text"]
    # A mutable supplier directory must not rewrite an approved invoice's source identity.
    with engine().begin() as db:
        db.execute(update(m.suppliers).values(name="Changed directory name"))
    fetched = client.get(f"/api/cases/{c['id']}").json()
    assert fetched["invoice"]["supplier"] == invoice["supplier"]
    assert fetched["approved_version"] == approved.json()["approved_version"]


def test_concurrent_retries_on_one_asgi_event_loop(client):
    import asyncio
    import httpx

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies=dict(client.cookies),
            headers={
                "X-CSRF-Token": client.cookies["pbp_csrf"],
                "Idempotency-Key": "same-loop-operation",
            },
        ) as worker:
            results = await asyncio.wait_for(
                asyncio.gather(*[worker.post("/api/invoices/sample") for _ in range(12)]),
                timeout=15,
            )
            assert all(r.status_code == 201 for r in results)
            assert len({r.json()["id"] for r in results}) == 1

    asyncio.run(exercise())
    assert len(client.get("/api/cases").json()) == 1
