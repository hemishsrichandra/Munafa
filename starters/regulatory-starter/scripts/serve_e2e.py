"""Disposable loopback browser fixture; no regulatory mock data, no production reset."""

import os
import sys
import uuid
import signal
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

load_dotenv(root / ".env")
url = os.getenv("TEST_DATABASE_URL", "")
if not url.startswith("postgresql+psycopg://"):
    raise SystemExit("Dedicated PostgreSQL TEST_DATABASE_URL required.")
schema = "starter_e2e_" + uuid.uuid4().hex
admin = create_engine(url)
child = None


def stop(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGTERM, stop)
try:
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    os.environ.update(
        DATABASE_URL=url,
        DATABASE_SCHEMA=schema,
        APP_ENV="test",
        ALLOW_DEV_LOGIN="0",
        APP_ORIGINS="http://127.0.0.1:8011",
    )
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    from backend.auth import provision

    provision(
        "synthetic-browser-owner",
        "synthetic-browser-password",
        "Synthetic foundation browser check",
        False,
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
        ],
        cwd=root,
        env=os.environ.copy(),
    )
    child.wait()
except KeyboardInterrupt:
    pass
finally:
    if child and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    if "backend.db" in sys.modules:
        sys.modules["backend.db"].engine().dispose()
    assert schema.startswith("starter_e2e_") and len(schema) == 44
    with admin.begin() as db:
        db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    admin.dispose()
