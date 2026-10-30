"""Synthetic account fixtures only; no fabricated regulatory source/result."""

import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail("A dedicated PostgreSQL TEST_DATABASE_URL is required.")
    schema = "starter_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_SCHEMA", schema)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_DEV_LOGIN", "0")
    try:
        command.upgrade(Config("alembic.ini"), "head")
        from backend.auth import provision
        from backend.app import app
        from backend.security import buckets

        buckets.clear()
        provision(
            "synthetic-test-owner", "synthetic-test-password", "Synthetic foundation test", False
        )
        with TestClient(app) as c:
            yield c
    finally:
        from backend.db import engine

        engine().dispose()
        assert schema.startswith("starter_test_") and len(schema) == 45
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def login(c):
    r = c.post(
        "/api/auth/login",
        json={"username": "synthetic-test-owner", "password": "synthetic-test-password"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_sessions_csrf_logout(client):
    assert client.get("/api/auth/me").status_code == 401
    data = login(client)
    assert client.get("/api/auth/me").json()["store"]["id"] == data["store"]["id"]
    assert client.post("/api/auth/logout").status_code == 403
    assert (
        client.post("/api/auth/logout", headers={"X-CSRF-Token": data["csrf"]}).status_code == 200
    )
    assert client.get("/api/auth/me").status_code == 401


def test_tenant_body_rejected_and_accounts_scoped(client):
    from backend.auth import provision
    from backend.app import app

    first = login(client)
    provision("synthetic-other", "synthetic-other-password", "Synthetic second account", False)
    with TestClient(app) as other:
        second = other.post(
            "/api/auth/login",
            json={"username": "synthetic-other", "password": "synthetic-other-password"},
        ).json()
        assert second["store"]["id"] != first["store"]["id"]
        assert (
            other.get("/api/auth/me", headers={"X-Store-ID": first["store"]["id"]}).json()["store"][
                "id"
            ]
            == second["store"]["id"]
        )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "x", "password": "PRIVATE_TEST_VALUE", "store_id": "spoof"},
        ).status_code
        == 422
    )
    assert (
        "PRIVATE_TEST_VALUE"
        not in client.post("/api/auth/login", json={"password": "PRIVATE_TEST_VALUE"}).text
    )


def test_database_and_clean_migration(client):
    from backend.db import engine
    from backend import models
    from sqlalchemy import inspect

    with engine().connect() as db:
        assert set(inspect(db).get_table_names()) == set(models.metadata.tables) | {
            "alembic_version"
        }
        assert (
            db.execute(text("select version_num from alembic_version")).scalar_one()
            == "foundation_0001"
        )
    command.check(Config("alembic.ini"))


def test_no_fake_regulatory_data_or_demo_login(client):
    assert client.get("/api/health").json() == {
        "ok": True,
        "foundation_only": True,
        "regulatory_sources_connected": False,
    }
    login(client)
    assert client.post(
        "/api/auth/dev-login",
        headers={
            "X-CSRF-Token": client.cookies.get("rp_csrf", ""),
            "Idempotency-Key": uuid.uuid4().hex,
        },
        json={"code": "not-a-real-access-code"},
    ).status_code in (404, 405)


def test_sensitive_login_rate_limit(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login", json={"username": "missing", "password": "incorrect"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"username": "missing", "password": "incorrect"}
        ).status_code
        == 429
    )


def test_idempotency_exact_request_and_actor_binding(client):
    from backend.app import app
    from backend import auth
    from backend.db import engine
    from backend import models as m
    from sqlalchemy import select, func

    before = list(app.router.routes)
    try:

        @app.post("/api/test-only-probe")
        def probe():
            auth.current("write")
            return {"accepted": True}

        # Test-only route precedes the static SPA mount, just like real API routes.
        app.router.routes.insert(0, app.router.routes.pop())

        first = login(client)
        key = uuid.uuid4().hex
        headers = {"X-CSRF-Token": first["csrf"], "Idempotency-Key": key}
        a = client.post("/api/test-only-probe", json={"value": 1}, headers=headers)
        b = client.post("/api/test-only-probe", json={"value": 1}, headers=headers)
        assert a.status_code == b.status_code == 200 and b.headers["Idempotency-Replayed"] == "true"
        assert (
            client.post("/api/test-only-probe", json={"value": 2}, headers=headers).status_code
            == 409
        )
        with engine().connect() as db:
            assert (
                db.execute(
                    select(func.count())
                    .select_from(m.operations)
                    .where(m.operations.c.operation_key == key)
                ).scalar_one()
                == 1
            )
        auth.provision(
            "synthetic-colleague",
            "synthetic-colleague-password",
            "ignored",
            False,
            "staff",
            first["store"]["id"],
        )
        colleague = client.post(
            "/api/auth/login",
            json={"username": "synthetic-colleague", "password": "synthetic-colleague-password"},
        ).json()
        assert (
            client.post(
                "/api/test-only-probe",
                json={"value": 1},
                headers={**headers, "X-CSRF-Token": colleague["csrf"]},
            ).status_code
            == 409
        )
    finally:
        app.router.routes[:] = before


def test_viewer_write_denial_and_secure_cookie_configuration(client, monkeypatch):
    from backend import auth

    auth.provision(
        "synthetic-viewer", "synthetic-viewer-password", "Synthetic viewer", False, "viewer"
    )
    row = client.post(
        "/api/auth/login",
        json={"username": "synthetic-viewer", "password": "synthetic-viewer-password"},
    )
    assert row.status_code == 200
    assert (
        client.post(
            "/api/test-only-probe",
            headers={"X-CSRF-Token": row.json()["csrf"], "Idempotency-Key": uuid.uuid4().hex},
        ).status_code
        == 403
    )
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post(
        "/api/auth/login",
        json={"username": "synthetic-test-owner", "password": "synthetic-test-password"},
    )
    cookies = response.headers.get_list("set-cookie")
    assert all("Secure" in value and "SameSite=strict" in value for value in cookies)
    assert any("HttpOnly" in value and "rp_session=" in value for value in cookies)


def test_rollback_rehearsal_only_generated_disposable_schema(client):
    from backend.db import engine

    schema = os.environ["DATABASE_SCHEMA"]
    assert schema.startswith("starter_test_") and len(schema) == 45
    command.downgrade(Config("alembic.ini"), "base")
    command.upgrade(Config("alembic.ini"), "head")
    with engine().connect() as db:
        assert (
            db.execute(text("select version_num from alembic_version")).scalar_one()
            == "foundation_0001"
        )
