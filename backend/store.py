"""SQLite serializes mutations; optimistic versions guard stale browser tabs."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .domain import RuleError

DB_PATH = os.environ.get("MUNAFA_DB", ".data/munafa.db")


def _connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


@contextmanager
def connect():
    db = _connect()
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def init():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attachments (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), name TEXT NOT NULL, mime TEXT NOT NULL, data BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS synthetic_proofs (attachment_id TEXT PRIMARY KEY REFERENCES attachments(id), data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS resolution_proofs (supplier TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(supplier,digest));
        CREATE TABLE IF NOT EXISTS resolution_keys (supplier TEXT NOT NULL, reference TEXT NOT NULL, PRIMARY KEY(supplier,reference));
        """)


def get(db, case_id):
    row = db.execute("SELECT data FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        raise KeyError(case_id)
    return json.loads(row["data"])


def save(db, case):
    db.execute(
        "INSERT INTO cases(id,data) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
        (case["id"], json.dumps(case, ensure_ascii=False)),
    )


def all_cases():
    with connect() as db:
        return [
            json.loads(r["data"]) for r in db.execute("SELECT data FROM cases ORDER BY rowid DESC")
        ]


@contextmanager
def mutate(case_id, version):
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        case = get(db, case_id)
        if case["version"] != version:
            raise RuleError("This case changed in another tab. Reload it and try again.")
        yield db, case
        case["version"] += 1
        save(db, case)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
