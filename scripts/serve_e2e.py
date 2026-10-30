"""Disposable PostgreSQL E2E server; never touches the configured application schema."""

import os
import sys
import uuid
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv()

url = os.environ.get("TEST_DATABASE_URL", "")
if not url.startswith("postgresql+psycopg://"):
    raise SystemExit("TEST_DATABASE_URL is required; no fallback.")
schema = "e2e_" + uuid.uuid4().hex
admin = create_engine(url)
with admin.begin() as db:
    db.execute(text(f'CREATE SCHEMA "{schema}"'))
os.environ.update(
    DATABASE_URL=url,
    DATABASE_SCHEMA=schema,
    APP_ENV="test",
    ALLOW_DEV_LOGIN="1",
    DEV_LOGIN_CODE="e2e-isolated-demo-access",
    SARVAM_API_KEY="",
)
try:
    command.upgrade(Config("alembic.ini"), "head")
    from backend import auth

    for name in (
        "offline-owner",
        "commerce-owner",
        "partner-owner",
        "commerce-offline",
        "offline-second",
        "offline-quota",
        "offline-expired",
        "offline-attachment",
        "offline-conflict",
    ):
        auth.provision(name, "isolated-browser-test-password", name + " synthetic", True)
    auth.demo_login(os.environ["DEV_LOGIN_CODE"])
    # Workflow tests create their own explicitly labelled invoices.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
        check=True,
    )
finally:
    assert schema.startswith("e2e_") and len(schema) == 36
    with admin.begin() as db:
        db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
