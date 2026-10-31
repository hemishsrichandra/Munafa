"""Conservative public-demo provider gate. Reservations are not provider invoices."""

import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from . import auth, models as m
from .db import engine
from .domain import RuleError


BLOCKED = (
    "Cloud AI is unavailable in this public demo. Use manual entry or your own merchant account."
)


def positive(name, maximum):
    value = os.getenv(name, "")
    if not value.isdecimal() or not 1 <= int(value) <= maximum:
        raise RuleError(BLOCKED)
    return int(value)


def public_settings_enabled():
    if os.getenv("PUBLIC_DEMO_AI_ENABLED", "0") != "1":
        return False
    try:
        request = positive("PUBLIC_DEMO_AI_REQUEST_RESERVE_PAISE", 10000)
        daily = positive("PUBLIC_DEMO_AI_DAILY_RESERVE_LIMIT_PAISE", 100000)
        positive("PUBLIC_DEMO_AI_GLOBAL_DAILY_CALLS", 1000)
        positive("PUBLIC_DEMO_AI_STORE_DAILY_CALLS", 100)
        return request <= daily
    except RuleError:
        return False


def reserve(purpose):
    p = auth.principal.get()
    if p is None:
        return None  # Trusted explicit operator tooling, never an unauthenticated HTTP route.
    if not p.public_demo:
        if not p.provider_access:
            raise RuleError(
                "Cloud AI is not enabled for this account. Use manual entry or ask your administrator."
            )
        return None
    # Zero paid public-demo calls by default, even if a backend provider key exists.
    if os.getenv("PUBLIC_DEMO_AI_ENABLED", "0") != "1":
        raise RuleError(BLOCKED)
    request_paise = positive("PUBLIC_DEMO_AI_REQUEST_RESERVE_PAISE", 10000)
    daily_paise = positive("PUBLIC_DEMO_AI_DAILY_RESERVE_LIMIT_PAISE", 100000)
    global_calls = positive("PUBLIC_DEMO_AI_GLOBAL_DAILY_CALLS", 1000)
    store_calls = positive("PUBLIC_DEMO_AI_STORE_DAILY_CALLS", 100)
    now = datetime.now(timezone.utc)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Independent committed reservation survives a failing downstream request/transaction.
    with engine().begin() as db:
        for scope, limit in (
            ("public-demo-global", global_calls),
            ("store:" + p.store_id, store_calls),
        ):
            db.execute(
                pg_insert(m.usage_counters)
                .values(scope=scope, window_start=day, calls=0, reserved_paise=0)
                .on_conflict_do_nothing()
            )
            row = (
                db.execute(
                    select(m.usage_counters)
                    .where(
                        m.usage_counters.c.scope == scope, m.usage_counters.c.window_start == day
                    )
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if row["calls"] >= limit or row["reserved_paise"] + request_paise > daily_paise:
                raise RuleError(BLOCKED)
            db.execute(
                update(m.usage_counters)
                .where(m.usage_counters.c.scope == scope, m.usage_counters.c.window_start == day)
                .values(
                    calls=row["calls"] + 1, reserved_paise=row["reserved_paise"] + request_paise
                )
            )
        rid = uuid.uuid4().hex
        db.execute(
            insert(m.usage_events).values(
                id=rid,
                store_id=p.store_id,
                actor_id=p.user_id,
                purpose=purpose,
                reserved_paise=request_paise,
                window_start=day,
                at=now,
            )
        )
        return rid
