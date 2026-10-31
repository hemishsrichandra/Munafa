"""Public onboarding uses PostgreSQL transactions and isolated synthetic tenants."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from backend import auth, models as m
from backend.app import app
from backend.db import engine
from backend.security import buckets

PASSWORD = "synthetic-test-password-long"


def signup(c, username="new-owner", **extra):
    return c.post(
        "/api/auth/signup",
        json={"username": username, "password": PASSWORD, "store_name": "New test kirana", **extra},
    )


def test_signup_session_and_private_empty_store(database):
    with TestClient(app) as c:
        r = signup(c, " New.Owner ")
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "owner"
        assert r.json()["store"]["demo"] is False
        assert r.json()["store"]["timezone"] == "Asia/Kolkata"
        assert "session_token" not in r.json()
        assert c.get("/api/auth/me").status_code == 200
        assert c.get("/api/cases").json() == []
        assert c.post("/api/actions", json={"action_type": "export_ledger"}).status_code == 403
        csrf = c.cookies["pbp_csrf"]
        assert c.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert c.get("/api/auth/me").status_code == 401
        assert (
            c.post(
                "/api/auth/login", json={"username": "new.owner", "password": PASSWORD}
            ).status_code
            == 200
        )
    with engine().connect() as db:
        row = db.execute(select(m.users)).mappings().one()
        assert row["username"] == "new.owner"
        assert row["password_hash"] != PASSWORD
        assert auth.password_valid(PASSWORD, row["password_hash"])


def test_signup_duplicate_case_and_no_orphan_tenants(database):
    with TestClient(app) as c:
        assert signup(c, "Merchant").status_code == 201
        assert signup(c, "MERCHANT").status_code == 409
    with engine().connect() as db:
        for table in (m.users, m.stores, m.merchants, m.memberships, m.sessions):
            assert db.execute(select(func.count()).select_from(table)).scalar_one() == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"username": "x"},
        {"username": "demo-secret"},
        {"username": "munafa-demo"},
        {"password": "short"},
        {"password": " " * 12},
        {"store_name": " "},
        {"store_name": "bad\nname"},
        {"role": "owner"},
        {"store_id": "spoof"},
        {"demo": True},
        {"username": "a<script>"},
    ],
)
def test_signup_validation_no_client_tenant_or_role(database, extra):
    with TestClient(app) as c:
        assert signup(c, **extra).status_code == 422
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.users)).scalar_one() == 0


def test_public_demo_isolated_seeded_and_not_recovered(database):
    with TestClient(app) as a, TestClient(app) as b:
        ra = a.post("/api/auth/demo", json={})
        rb = b.post("/api/auth/demo", json={})
        assert ra.status_code == rb.status_code == 201
        assert ra.json()["store"]["demo"] is True
        assert ra.json()["store"]["id"] != rb.json()["store"]["id"]
        cases = a.get("/api/cases").json()
        assert len(cases) == len(b.get("/api/cases").json()) == 1
        assert cases[0]["synthetic"] is True
        assert cases[0]["status"] == "review"
        assert all(line["received"] is None for line in cases[0]["invoice"]["lines"])
        assert b.get("/api/cases/" + cases[0]["id"]).status_code == 404
        buckets.clear()
        real = TestClient(app)
        assert signup(real, "real-owner").status_code == 201
        assert real.get("/api/cases").json() == []
        assert real.get("/api/cases/" + cases[0]["id"]).status_code == 404
        assert (
            real.post("/api/auth/demo", json={"store_id": ra.json()["store"]["id"]}).status_code
            == 422
        )


def test_demo_seed_failure_rolls_back_entire_identity(database, monkeypatch):
    def broken():
        raise RuntimeError("intentional synthetic fixture failure")

    monkeypatch.setattr("backend.samples.demo_seed", broken)
    with TestClient(app) as c, pytest.raises(RuntimeError):
        c.post("/api/auth/demo", json={})
    with engine().connect() as db:
        for table in (m.users, m.stores, m.merchants, m.memberships, m.sessions, m.cases):
            assert db.execute(select(func.count()).select_from(table)).scalar_one() == 0


def test_public_flags_and_cap_work_in_production(database, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_DEMO_MAX_STORES", "1")
    with TestClient(app, base_url="https://testserver") as c:
        assert c.get("/api/health").json()["development_login"] is False
        r = c.post("/api/auth/demo", json={})
        assert r.status_code == 201
        assert "Secure" in r.headers.get_list("set-cookie")[0]
        assert "HttpOnly" in r.headers.get_list("set-cookie")[0]
        assert c.get("/api/auth/me").status_code == 200
        assert c.post("/api/auth/demo", json={}).status_code == 429
        monkeypatch.setenv("ENABLE_PUBLIC_SIGNUP", "0")
        monkeypatch.setenv("ENABLE_PUBLIC_DEMO", "0")
        buckets.clear()
        assert signup(c).status_code == 404
        assert c.post("/api/auth/demo", json={}).status_code == 404
        assert c.get("/api/health").json()["public_demo"] is False
        assert c.get("/api/health").json()["public_signup"] is False


def test_public_creation_rate_limit_and_origin(database, monkeypatch):
    monkeypatch.setenv("APP_ORIGINS", "https://app.example")
    with TestClient(app) as c:
        assert signup(c).status_code == 201
        assert (
            c.post(
                "/api/auth/demo", json={}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert c.post("/api/auth/demo", json={}).status_code == 201
        assert c.post("/api/auth/demo", json={}).status_code == 201
        assert c.post("/api/auth/demo", json={}).status_code == 429


def test_concurrent_signup_and_demo_caps_are_database_enforced(database, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException

    def register():
        try:
            return auth.signup("concurrent-owner", PASSWORD, "Synthetic concurrency store")[
                0
            ].store_id
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register(), range(2)))
    assert sum(isinstance(result, str) for result in results) == 1
    assert results.count(409) == 1
    monkeypatch.setenv("PUBLIC_DEMO_MAX_STORES", "1")

    def demo():
        try:
            return auth.public_demo()[0].store_id
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: demo(), range(2)))
    assert sum(isinstance(result, str) for result in results) == 1
    assert results.count(429) == 1
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.stores)).scalar_one() == 2


def test_signup_session_failure_is_atomic_and_legacy_case_collision(database, monkeypatch):
    auth.provision("Legacy.Owner", PASSWORD, "Synthetic legacy store")
    with TestClient(app) as c:
        assert signup(c, "legacy.owner").status_code == 409

    def broken(*args):
        raise RuntimeError("intentional session creation failure")

    monkeypatch.setattr(auth, "session_for", broken)
    with TestClient(app) as c, pytest.raises(RuntimeError):
        signup(c, "rollback-owner")
    with engine().connect() as db:
        for table in (m.users, m.stores, m.merchants, m.memberships):
            assert db.execute(select(func.count()).select_from(table)).scalar_one() == 1


def test_empty_database_startup_never_provisions_default_owner(database):
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 200
    with engine().connect() as db:
        assert db.execute(select(func.count()).select_from(m.users)).scalar_one() == 0


def test_cli_password_rotation_revokes_sessions_without_changing_store_data(database):
    auth.provision("rotate-owner", PASSWORD, "Synthetic rotation store")
    with TestClient(app) as c:
        assert (
            c.post(
                "/api/auth/login", json={"username": "rotate-owner", "password": PASSWORD}
            ).status_code
            == 200
        )
        sid = c.get("/api/auth/me").json()["store"]["id"]
        auth.change_password("rotate-owner", "new-synthetic-rotation-password")
        assert c.get("/api/auth/me").status_code == 401
        assert (
            c.post(
                "/api/auth/login", json={"username": "rotate-owner", "password": PASSWORD}
            ).status_code
            == 401
        )
        assert (
            c.post(
                "/api/auth/login",
                json={"username": "rotate-owner", "password": "new-synthetic-rotation-password"},
            ).status_code
            == 200
        )
        assert c.get("/api/auth/me").json()["store"]["id"] == sid
    with pytest.raises(ValueError):
        auth.change_password("rotate-owner", "short")
    with pytest.raises(ValueError):
        auth.change_password("missing-owner", "new-synthetic-rotation-password")
