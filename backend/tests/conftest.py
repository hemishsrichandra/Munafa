"""Every test uses a new PostgreSQL schema. Never falls back to another database."""

import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config


@pytest.fixture
def database(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        pytest.fail("TEST_DATABASE_URL must point to a dedicated PostgreSQL test database.")
    schema = "test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_SCHEMA", schema)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_DEV_LOGIN", "0")
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    command.upgrade(Config("alembic.ini"), "head")
    from backend.security import buckets

    buckets.clear()
    yield schema
    from backend.db import engine

    engine().dispose()
    # Only this fixture's generated disposable schema can be removed.
    assert schema.startswith("test_") and len(schema) == 37
    with admin.begin() as db:
        db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.auth import provision

    provision("test-owner", "test-password-long", "Test synthetic store", True)

    class AuthClient(TestClient):
        def request(self, method, url, **kwargs):
            headers = dict(kwargs.pop("headers", {}) or {})
            if method.upper() not in ("GET", "HEAD", "OPTIONS"):
                headers.setdefault("X-CSRF-Token", self.cookies.get("pbp_csrf", ""))
                headers.setdefault("Idempotency-Key", uuid.uuid4().hex)
            return super().request(method, url, headers=headers, **kwargs)

    with AuthClient(app) as c:
        r = c.post(
            "/api/auth/login", json={"username": "test-owner", "password": "test-password-long"}
        )
        assert r.status_code == 200, r.text
        yield c
