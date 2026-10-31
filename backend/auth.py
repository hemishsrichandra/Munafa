"""Password sessions and explicit development-only demo access. No Paytm identity claims."""

import hashlib
import hmac
import os
import re
import secrets
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, insert, delete, text, func, update
from sqlalchemy.exc import IntegrityError
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
    public_demo: bool = False
    provider_access: bool = False


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
    username, password, store_name="Kirana store", demo=False, role="owner", store_id=None
):
    """Explicit CLI/test provisioning, not a public registration endpoint."""
    with engine().begin() as db:
        return provision_in(
            db,
            username,
            password_hash(password),
            store_name,
            demo,
            role,
            store_id,
            provider_access=True,
        )


def provision_in(
    db, username, hashed, store_name, demo=False, role="owner", store_id=None, provider_access=False
):
    """Identity, membership and session creation can share one atomic transaction."""
    uid = uuid.uuid4().hex
    sid = store_id or uuid.uuid4().hex
    if store_id is None:
        mid = uuid.uuid4().hex
        db.execute(insert(m.merchants).values(id=mid, name=store_name))
        db.execute(
            insert(m.stores).values(
                id=sid, merchant_id=mid, name=store_name, timezone="Asia/Kolkata", demo=demo
            )
        )
    db.execute(
        insert(m.users).values(
            id=uid, username=username, password_hash=hashed, provider_access=provider_access
        )
    )
    db.execute(insert(m.memberships).values(user_id=uid, store_id=sid, role=role))
    return uid, sid


def public_signup_enabled():
    return os.getenv("ENABLE_PUBLIC_SIGNUP", "1") == "1"


def public_demo_enabled():
    return os.getenv("ENABLE_PUBLIC_DEMO", "1") == "1"


def signup(username, password, store_name):
    if not public_signup_enabled():
        raise HTTPException(404, "Account creation is unavailable. Contact your administrator.")
    username = username.strip().lower()
    store_name = store_name.strip()
    if (
        not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,59}", username)
        or username.startswith("demo-")
        or username == "munafa-demo"
    ):
        raise HTTPException(
            422,
            "Use 3–60 letters, numbers, dots, underscores or hyphens for your username. Demo names are reserved.",
        )
    if not 12 <= len(password) <= 200 or not password.strip():
        raise HTTPException(422, "Use a password with 12–200 characters.")
    if not 1 <= len(store_name) <= 120 or re.search(r"[\x00-\x1f\x7f]", store_name):
        raise HTTPException(422, "Enter a store name with 1–120 characters.")
    hashed = password_hash(password)
    try:
        with engine().begin() as db:
            # Serialize public registrations; also respect case variants of legacy CLI accounts.
            db.execute(text("SELECT pg_advisory_xact_lock(7042196001)"))
            if db.execute(
                select(m.users.c.id).where(func.lower(m.users.c.username) == username)
            ).first():
                raise HTTPException(409, "That username is unavailable. Choose another or sign in.")
            uid, sid = provision_in(db, username, hashed, store_name)
            return session_for(db, uid, sid)
    except IntegrityError:
        raise HTTPException(
            409, "That username is unavailable. Choose another or sign in."
        ) from None


def public_demo():
    """New private synthetic tenant per visitor; never a shared production credential."""
    if not public_demo_enabled():
        raise HTTPException(404, "The demo is unavailable. You can create a merchant account.")
    try:
        limit = int(os.getenv("PUBLIC_DEMO_MAX_STORES", "500"))
        if not 1 <= limit <= 10000:
            raise ValueError
    except ValueError:
        raise HTTPException(503, "The demo is temporarily unavailable.") from None
    hashed = password_hash(secrets.token_urlsafe(48))
    with engine().begin() as db:
        # Database-wide cap works across workers/restarts, unlike the per-process IP limiter.
        db.execute(text("SELECT pg_advisory_xact_lock(7042196002)"))
        count = db.execute(
            select(func.count())
            .select_from(m.users)
            .join(m.memberships, m.memberships.c.user_id == m.users.c.id)
            .join(m.stores, m.stores.c.id == m.memberships.c.store_id)
            .where(m.users.c.username.startswith("demo-"), m.stores.c.demo.is_(True))
        ).scalar_one()
        if count >= limit:
            raise HTTPException(
                429,
                "Demo capacity reached. Create an account or try again after the administrator makes space available.",
            )
        uid, sid = provision_in(
            db, "demo-" + uuid.uuid4().hex, hashed, "Your demo kirana · synthetic", demo=True
        )
        result = session_for(db, uid, sid)
        # Seed the existing invoice through its existing domain rules, in this same transaction.
        from . import store
        from .samples import demo_seed

        principal_token = principal.set(result[0])
        connection_token = store.request_connection.set(db)
        try:
            demo_seed()
        finally:
            store.request_connection.reset(connection_token)
            principal.reset(principal_token)
        return result


def membership(db, uid, sid=None):
    q = (
        select(
            m.memberships,
            m.stores.c.timezone,
            m.stores.c.demo,
            m.stores.c.name,
            m.users.c.username,
            m.users.c.provider_access,
        )
        .join(m.stores, m.memberships.c.store_id == m.stores.c.id)
        .join(m.users, m.memberships.c.user_id == m.users.c.id)
        .where(m.memberships.c.user_id == uid)
    )
    if sid:
        q = q.where(m.memberships.c.store_id == sid)
    row = db.execute(q.order_by(m.memberships.c.store_id)).mappings().first()
    if not row:
        raise HTTPException(403, "Store access denied.")
    return Principal(
        uid,
        row["store_id"],
        row["role"],
        row["timezone"],
        row["demo"],
        row["name"],
        bool(row["demo"] and row["username"].startswith("demo-")),
        row["provider_access"],
    )


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
        row = (
            db.execute(select(m.users).where(m.users.c.username == username).with_for_update())
            .mappings()
            .first()
        )
        if row is None:
            row = (
                db.execute(
                    select(m.users)
                    .where(m.users.c.username == username.strip().lower())
                    .with_for_update()
                )
                .mappings()
                .first()
            )
        # Equal-cost password work for unknown usernames.
        stored = row["password_hash"] if row else "0" * 32 + ":" + "0" * 128
        if not password_valid(password, stored) or row is None:
            raise HTTPException(401, "Invalid username or password.")
        return session_for(db, row["id"])


def change_password(username, password):
    """Administrator-only CLI operation; never exposed as an unauthenticated endpoint."""
    if not 12 <= len(password) <= 200 or not password.strip():
        raise ValueError("Use a password with 12–200 characters.")
    hashed = password_hash(password)
    with engine().begin() as db:
        row = db.execute(
            select(m.users.c.id).where(m.users.c.username == username).with_for_update()
        ).first()
        if not row:
            raise ValueError("Account not found. No password was changed.")
        db.execute(update(m.users).where(m.users.c.id == row.id).values(password_hash=hashed))
        db.execute(delete(m.sessions).where(m.sessions.c.user_id == row.id))
        from .recovery import revoke_codes

        revoke_codes(db, row.id)


def set_provider_access(username, enabled):
    """Trusted operator CLI only; store owners cannot approve their own shared-key spending."""
    with engine().begin() as db:
        row = db.execute(
            select(m.users.c.id).where(m.users.c.username == username).with_for_update()
        ).first()
        if not row:
            raise ValueError("Account not found. No change made.")
        p = membership(db, row.id)
        if p.public_demo:
            raise ValueError(
                "Public demos use the separate global quota gate, not account approval."
            )
        db.execute(
            update(m.users).where(m.users.c.id == row.id).values(provider_access=bool(enabled))
        )


def demo_login(code):
    if not development_login():
        raise HTTPException(404, "Not available.")
    if not hmac.compare_digest(code, os.getenv("DEV_LOGIN_CODE", "")):
        raise HTTPException(401, "Invalid demo access code.")
    with engine().begin() as db:
        row = db.execute(select(m.users.c.id).where(m.users.c.username == "munafa-demo")).first()
    if not row:
        uid, _ = provision(
            "munafa-demo", secrets.token_urlsafe(48), "Lakshmi Kirana · synthetic demo", True
        )
    else:
        uid = row.id
    with engine().begin() as db:
        p, token, csrf = session_for(db, uid)
        if not p.demo:
            raise HTTPException(403, "Demo login requires an isolated demo store.")
        return p, token, csrf


def revoke(token):
    with engine().begin() as db:
        db.execute(delete(m.sessions).where(m.sessions.c.token_hash == digest(token)))
