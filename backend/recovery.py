"""One-time offline recovery: no email service, raw-code persistence or auto-login."""

import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, insert, update, delete, func
from . import auth, models as m, store
from .db import engine

router = APIRouter(prefix="/api/auth")
DENIED = "Account recovery could not be verified. Check your username and unused recovery code."


class AuthInput(BaseModel):
    # Passwords preserve exact bytes, including leading/trailing spaces.
    model_config = ConfigDict(extra="forbid")


class Reauthenticate(AuthInput):
    password: str = Field(min_length=1, max_length=200)


class Recover(AuthInput):
    username: str = Field(min_length=1, max_length=120)
    recovery_code: str = Field(min_length=1, max_length=80)
    new_password: str = Field(min_length=12, max_length=200)


def code_digest(value):
    normal = value.replace("-", "").replace(" ", "").upper()
    # Unknown/malformed codes follow the same generic failure path.
    return auth.digest(normal if re.fullmatch(r"[0-9A-F]{32}", normal) else "invalid-code")


def revoke_codes(db, uid, at=None):
    db.execute(
        update(m.recovery_codes)
        .where(m.recovery_codes.c.user_id == uid, m.recovery_codes.c.revoked_at.is_(None))
        .values(revoked_at=at or datetime.now(timezone.utc))
    )


@router.get("/privacy")
def privacy_policy():
    auth.current()
    from .retention import POLICY

    return POLICY


@router.get("/security")
def security_status():
    p = auth.current()
    now = datetime.now(timezone.utc)
    with store.connect() as db:
        count = db.execute(
            select(func.count())
            .select_from(m.recovery_codes)
            .where(
                m.recovery_codes.c.user_id == p.user_id,
                m.recovery_codes.c.used_at.is_(None),
                m.recovery_codes.c.revoked_at.is_(None),
                m.recovery_codes.c.expires_at > now,
            )
        ).scalar_one()
        username = db.execute(
            select(m.users.c.username).where(m.users.c.id == p.user_id)
        ).scalar_one()
    return {
        "username": username,
        "remaining_codes": count,
        "recovery_available": not p.public_demo,
        "email_recovery_available": False,
        "provider_access_approved": p.provider_access,
    }


@router.post("/recovery-codes", status_code=201)
def issue_codes(body: Reauthenticate):
    p = auth.current()
    if p.public_demo:
        raise HTTPException(
            403,
            "Recovery codes are for your own merchant account. Create an account outside the demo.",
        )
    with store.connect() as db:
        user = (
            db.execute(select(m.users).where(m.users.c.id == p.user_id).with_for_update())
            .mappings()
            .one()
        )
        if not auth.password_valid(body.password, user["password_hash"]):
            raise HTTPException(401, "Re-enter your current password to manage recovery codes.")
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=365)
        revoke_codes(db, p.user_id, now)
        codes = [secrets.token_hex(16).upper() for _ in range(8)]
        db.execute(
            insert(m.recovery_codes),
            [
                {
                    "id": uuid.uuid4().hex,
                    "user_id": p.user_id,
                    "code_hash": code_digest(code),
                    "created_at": now,
                    "expires_at": expires,
                }
                for code in codes
            ],
        )
        store.audit_record(
            db,
            p.user_id,
            "Account recovery codes rotated",
            entity_type="account_security",
            source_ids=[p.user_id],
        )
    return {
        "codes": ["-".join(code[i : i + 8] for i in range(0, 32, 8)) for code in codes],
        "username": user["username"],
        "expires_at": expires,
        "shown_once": True,
    }


@router.post("/recover")
def recover(body: Recover):
    if not body.new_password.strip():
        raise HTTPException(422, "Choose a password with at least 12 characters.")
    # Comparable password hashing work for known/unknown accounts; never log inputs.
    hashed = auth.password_hash(body.new_password)
    digest = code_digest(body.recovery_code)
    with engine().begin() as db:
        username = body.username.strip()
        user = (
            db.execute(select(m.users).where(m.users.c.username == username).with_for_update())
            .mappings()
            .first()
        )
        if user is None:
            user = (
                db.execute(
                    select(m.users).where(m.users.c.username == username.lower()).with_for_update()
                )
                .mappings()
                .first()
            )
        # Always execute a code lookup; dummy user is not a real identity.
        row = (
            db.execute(
                select(m.recovery_codes)
                .where(
                    m.recovery_codes.c.user_id == (user["id"] if user else "unknown"),
                    m.recovery_codes.c.code_hash == digest,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        now = datetime.now(timezone.utc)
        if (
            user is None
            or row is None
            or row["used_at"]
            or row["revoked_at"]
            or row["expires_at"] <= now
            or not hmac.compare_digest(row["code_hash"], digest)
        ):
            raise HTTPException(401, DENIED)
        p = auth.membership(db, user["id"])
        if p.public_demo:
            raise HTTPException(401, DENIED)
        db.execute(
            update(m.recovery_codes).where(m.recovery_codes.c.id == row["id"]).values(used_at=now)
        )
        revoke_codes(db, user["id"], now)
        db.execute(update(m.users).where(m.users.c.id == user["id"]).values(password_hash=hashed))
        db.execute(delete(m.sessions).where(m.sessions.c.user_id == user["id"]))
        ctx = auth.principal.set(p)
        try:
            store.audit_record(
                db,
                user["id"],
                "Password recovered; all sessions and remaining codes revoked",
                entity_type="account_security",
                source_ids=[user["id"]],
            )
        finally:
            auth.principal.reset(ctx)
    return {
        "ok": True,
        "detail": "Password changed. Sign in with your new password, then create new recovery codes.",
    }
