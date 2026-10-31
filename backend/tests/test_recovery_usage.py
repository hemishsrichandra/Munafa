"""Own-account recovery and public-demo provider gates, PostgreSQL only."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update, func
from sqlalchemy.exc import DBAPIError
from backend import auth, models as m, usage, ai, providers
from backend.app import app
from backend.db import engine
from backend.domain import RuleError
from backend.tests.test_trust import other_client

PASSWORD = "test-password-long"
NEW = "  new-password-with-exact-spaces  "


def issue(client, password=PASSWORD):
    r = client.post("/api/auth/recovery-codes", json={"password": password})
    assert r.status_code == 201, r.text
    return r.json()


def reset(c, code, username="test-owner", new_password=NEW):
    return c.post(
        "/api/auth/recover",
        json={"username": username, "recovery_code": code, "new_password": new_password},
    )


def test_hash_only_rotation_single_use_and_session_revocation(client):
    first = issue(client)
    assert len(first["codes"]) == len(set(first["codes"])) == 8
    assert client.get("/api/auth/security").json()["remaining_codes"] == 8
    with engine().connect() as db:
        rows = list(db.execute(select(m.recovery_codes)).mappings())
        assert all(len(r["code_hash"]) == 64 for r in rows)
        assert not any(code in str(rows) for code in first["codes"])
    rotated = issue(client)
    outsider = TestClient(app)
    assert reset(outsider, first["codes"][0]).status_code == 401
    r = reset(outsider, rotated["codes"][0])
    assert r.status_code == 200 and "session_token" not in r.json()
    assert not outsider.cookies.get("pbp_session")
    assert client.get("/api/auth/me").status_code == 401
    assert reset(outsider, rotated["codes"][0]).status_code == 401
    assert (
        client.post("/api/auth/login", json={"username": "test-owner", "password": NEW}).status_code
        == 200
    )
    assert client.get("/api/auth/security").json()["remaining_codes"] == 0
    assert (
        client.post(
            "/api/auth/login", json={"username": "test-owner", "password": NEW.strip()}
        ).status_code
        == 401
    )
    with engine().connect() as db:
        events = [dict(r) for r in db.execute(select(m.audit_events)).mappings()]
        raw = json.dumps(events, default=str)
        assert NEW not in raw and not any(code in raw for code in first["codes"] + rotated["codes"])


def test_expired_wrong_user_and_unknown_code_are_generic_and_non_destructive(client):
    codes = issue(client)["codes"]
    with engine().begin() as db:
        db.execute(
            update(m.recovery_codes).values(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                created_at=datetime.now(timezone.utc) - timedelta(days=2),
            )
        )
    outsider = TestClient(app)
    a = reset(outsider, codes[0])
    b = reset(outsider, codes[0], username="unknown-owner")
    c = reset(outsider, "invalid")
    assert a.status_code == b.status_code == c.status_code == 401
    assert a.json() == b.json() == c.json()
    assert client.get("/api/auth/me").status_code == 200
    assert reset(outsider, "invalid").status_code == 429


def test_only_current_user_can_issue_codes_and_viewer_can_logout(client):
    assert client.post("/api/auth/recovery-codes", json={"password": "wrong"}).status_code == 401
    assert (
        client.post(
            "/api/auth/recovery-codes", json={"password": PASSWORD, "user_id": "spoof"}
        ).status_code
        == 422
    )
    viewer, _ = other_client("viewer")
    issued = issue(viewer, "long-test-password")
    assert len(issued["codes"]) == 8
    assert (
        viewer.post("/api/products", json={"code": "DENY", "name": "No", "unit": "kg"}).status_code
        == 403
    )
    assert viewer.post("/api/auth/logout").status_code == 200


def test_wrong_username_does_not_consume_valid_code(client):
    code = issue(client)["codes"][0]
    other, _ = other_client()
    assert reset(other, code, username="not-this-owner").status_code == 401
    assert reset(other, code).status_code == 200


def test_concurrent_recovery_consumes_once(client):
    code = issue(client)["codes"][0]

    def call(_):
        with TestClient(app) as c:
            return reset(c, code).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(call, range(2)))
    assert sorted(statuses) == [200, 401]
    with engine().connect() as db:
        assert (
            db.execute(
                select(func.count())
                .select_from(m.recovery_codes)
                .where(m.recovery_codes.c.used_at.is_not(None))
            ).scalar_one()
            == 1
        )


def test_cli_password_rotation_revokes_recovery_codes(client):
    code = issue(client)["codes"][0]
    auth.change_password("test-owner", "new-cli-test-password-long")
    assert reset(TestClient(app), code).status_code == 401


def test_public_demo_cannot_enrol_or_recover_and_paid_calls_block_before_network(
    database, monkeypatch
):
    with TestClient(app) as c:
        r = c.post("/api/auth/demo", json={})
        assert r.status_code == 201
        c.headers.update({"X-CSRF-Token": r.json()["csrf"], "Idempotency-Key": uuid.uuid4().hex})
        assert c.get("/api/auth/security").json()["recovery_available"] is False
        assert c.post("/api/auth/recovery-codes", json={"password": PASSWORD}).status_code == 403
        p = auth.authenticate(c.cookies["pbp_session"])
        assert p.public_demo is True
        ctx = auth.principal.set(p)
        monkeypatch.setenv("SARVAM_API_KEY", "synthetic-not-a-real-key")

        def forbidden(*args, **kwargs):
            pytest.fail("Public demo must not contact a paid provider by default")

        monkeypatch.setattr("httpx.post", forbidden)
        try:
            with pytest.raises(RuleError):
                ai.post("/v2/chat/completions", {"max_tokens": 10})
            with pytest.raises(RuleError):
                providers.SarvamSpeech().transcribe(b"RIFF0000WAVE", "audio/wav", "en-IN")
        finally:
            auth.principal.reset(ctx)
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.usage_events)).scalar_one() == 0


def test_public_demo_quota_is_cross_worker_atomic_and_append_only(database, monkeypatch):
    p, _, _ = auth.public_demo()
    for name, value in {
        "PUBLIC_DEMO_AI_ENABLED": "1",
        "PUBLIC_DEMO_AI_REQUEST_RESERVE_PAISE": "25",
        "PUBLIC_DEMO_AI_DAILY_RESERVE_LIMIT_PAISE": "25",
        "PUBLIC_DEMO_AI_GLOBAL_DAILY_CALLS": "1",
        "PUBLIC_DEMO_AI_STORE_DAILY_CALLS": "1",
    }.items():
        monkeypatch.setenv(name, value)

    def reserve(_):
        ctx = auth.principal.set(p)
        try:
            try:
                return usage.reserve("document_or_text")
            except RuleError:
                return None
        finally:
            auth.principal.reset(ctx)

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(reserve, range(2)))
    assert sum(value is not None for value in ids) == 1
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.usage_events)).scalar_one() == 1
        rows = list(db.execute(select(m.usage_counters)).mappings())
        assert len(rows) == 2 and all(r["calls"] == 1 and r["reserved_paise"] == 25 for r in rows)
    with pytest.raises(DBAPIError), engine().begin() as db:
        db.execute(update(m.usage_events).values(reserved_paise=50))


def test_signup_preserves_password_spaces(client):
    r = client.post(
        "/api/auth/signup",
        json={"username": "spaced-owner", "password": NEW, "store_name": "Synthetic spaced store"},
    )
    assert r.status_code == 201
    c = TestClient(app)
    assert (
        c.post("/api/auth/login", json={"username": "spaced-owner", "password": NEW}).status_code
        == 200
    )
    assert (
        c.post(
            "/api/auth/login", json={"username": "spaced-owner", "password": NEW.strip()}
        ).status_code
        == 401
    )


def test_public_demo_capabilities_do_not_advertise_disabled_cloud_ai(database, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "synthetic-not-a-real-key")
    with TestClient(app) as c:
        assert c.post("/api/auth/demo", json={}).status_code == 201
        response = c.get("/api/assistant/capabilities")
        assert response.status_code == 200
        assert response.json()["cloud_configured"] is False
        assert response.json()["public_demo_provider_access"] is False
        assert c.get("/api/auth/privacy").json()["version"] == "retention-v1"


def test_unverified_public_signup_cannot_bypass_demo_spend_protection(database, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "synthetic-not-a-real-key")
    with TestClient(app) as c:
        r = c.post(
            "/api/auth/signup",
            json={
                "username": "unverified-owner",
                "password": "synthetic-password-long",
                "store_name": "Synthetic unverified store",
            },
        )
        assert r.status_code == 201
        p = auth.authenticate(c.cookies["pbp_session"])
        assert p.public_demo is False and p.provider_access is False
        assert c.get("/api/assistant/capabilities").json()["cloud_configured"] is False
        ctx = auth.principal.set(p)
        try:
            with pytest.raises(RuleError):
                usage.reserve("document_or_text")
        finally:
            auth.principal.reset(ctx)
        auth.set_provider_access("unverified-owner", True)
        assert c.get("/api/assistant/capabilities").json()["cloud_configured"] is True
        auth.set_provider_access("unverified-owner", False)
        assert c.get("/api/assistant/capabilities").json()["cloud_configured"] is False
