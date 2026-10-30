"""Minimal tenant-scoped infrastructure; no Munafa business repositories."""

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from .db import engine
from .auth import current
from .domain import RuleError

request_connection = ContextVar("request_connection", default=None)


def uid():
    return uuid.uuid4().hex


def scope(table):
    return table.c.store_id == current().store_id


def stamp(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def quantity(value):
    return (
        int(value)
        if value is not None and value == value.to_integral()
        else (str(value) if value is not None else None)
    )


@contextmanager
def connect(permission="read"):
    current(permission)
    try:
        active = request_connection.get()
        if active is not None:
            yield active
        else:
            with engine().begin() as db:
                yield db
    except IntegrityError:
        raise RuleError(
            "A duplicate reference or conflicting record already exists. Reload and review the existing case."
        ) from None
