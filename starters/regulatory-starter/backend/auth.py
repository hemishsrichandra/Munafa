"""Password sessions and explicit development-only demo access. No Paytm identity claims."""

import hashlib
import hmac
import os
import secrets
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, insert, delete
from fastapi import HTTPException
from .db import engine
from . import models as m


@dataclass(frozen=True)
class Principal:
    user_id: str
    store_id: str
    role: str
    timezone: str
    demo: bool
    store_name: str


principal: ContextVar[Principal | None] = ContextVar("principal", default=None)
PERMISSIONS = {
    "owner": {"read", "write", "approve", "messaging", "export", "admin"},
    "staff": {"read", "write"},
    "viewer": {"read"},
}


def current(permission="read"):
    p = principal.get()
    if p is None:
        raise HTTPException(401, "Sign in to continue.")
    if permission not in PERMISSIONS[p.role]:
        raise HTTPException(403, "Your role cannot perform this action.")
    return p


def development_login():
    if os.getenv("APP_ENV", "production") not in ("production", "development", "test"):
        raise RuntimeError("APP_ENV must be production, development or test.")
    enabled = os.getenv("ALLOW_DEV_LOGIN") == "1"
    if enabled and os.getenv("APP_ENV", "production") not in ("development", "test"):
        raise RuntimeError("Development login is forbidden outside development/test.")
    if enabled and len(os.getenv("DEV_LOGIN_CODE", "")) < 16:
        raise RuntimeError("DEV_LOGIN_CODE must contain at least 16 characters.")
    return enabled


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password):
    salt = secrets.token_hex(16)
    return (
        salt + ":" + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def password_valid(password, stored):
    try:
        salt, expected = stored.split(":")
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def provision(
    username, password, store_name="Business workspace", demo=False, role="owner", store_id=None
):
    """Explicit CLI/test provisioning, not a public registration endpoint."""
    uid = uuid.uuid4().hex
    sid = store_id or uuid.uuid4().hex
    with engine().begin() as db:
        if store_id is None:
            mid = uuid.uuid4().hex
            db.execute(insert(m.merchants).values(id=mid, name=store_name))
            db.execute(
                insert(m.stores).values(
                    id=sid, merchant_id=mid, name=store_name, timezone="Asia/Kolkata", demo=demo
                )
            )
        db.execute(
            insert(m.users).values(id=uid, username=username, password_hash=password_hash(password))
        )
        db.execute(insert(m.memberships).values(user_id=uid, store_id=sid, role=role))
    return uid, sid


def membership(db, uid, sid=None):
    q = (
        select(m.memberships, m.stores.c.timezone, m.stores.c.demo, m.stores.c.name)
        .join(m.stores, m.memberships.c.store_id == m.stores.c.id)
        .where(m.memberships.c.user_id == uid)
    )
    if sid:
        q = q.where(m.memberships.c.store_id == sid)
    row = db.execute(q.order_by(m.memberships.c.store_id)).mappings().first()
    if not row:
        raise HTTPException(403, "Store access denied.")
    return Principal(uid, row["store_id"], row["role"], row["timezone"], row["demo"], row["name"])


def session_for(db, uid, sid=None):
    p = membership(db, uid, sid)
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.execute(
        insert(m.sessions).values(
            id=uuid.uuid4().hex,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            user_id=uid,
            store_id=p.store_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        )
    )
    return p, token, csrf


def authenticate(token, csrf=None):
    with engine().begin() as db:
        row = (
            db.execute(select(m.sessions).where(m.sessions.c.token_hash == digest(token)))
            .mappings()
            .first()
        )
        if not row or row["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(401, "Session expired. Sign in again.")
        if csrf is not None and not hmac.compare_digest(row["csrf_hash"], digest(csrf)):
            raise HTTPException(403, "Security token is missing or expired. Reload and try again.")
        return membership(db, row["user_id"], row["store_id"])


def login(username, password):
    with engine().begin() as db:
        row = db.execute(select(m.users).where(m.users.c.username == username)).mappings().first()
        # Equal-cost password work for unknown usernames.
        stored = row["password_hash"] if row else "0" * 32 + ":" + "0" * 128
        if not password_valid(password, stored) or row is None:
            raise HTTPException(401, "Invalid username or password.")
        return session_for(db, row["id"])


def revoke(token):
    with engine().begin() as db:
        db.execute(delete(m.sessions).where(m.sessions.c.token_hash == digest(token)))
