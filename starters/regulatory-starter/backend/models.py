"""PostgreSQL schema. Alembic owns DDL; the application never creates tables."""

from sqlalchemy import (
    MetaData,
    Table,
    Column as C,
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint as U,
    CheckConstraint as Check,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def table(name, *cols):
    return Table(name, metadata, *cols)


def identity():
    return C("id", String(64), primary_key=True)


def scoped():
    return C("store_id", String(64), ForeignKey("stores.id"), nullable=False, index=True)


def instant(name):
    return C(name, DateTime(timezone=True), nullable=False)


def owned(name, target):
    return ForeignKeyConstraint(["store_id", name], [f"{target}.store_id", f"{target}.id"])


def owned_unique():
    return U("store_id", "id")


merchants = table("merchants", identity(), C("name", String(120), nullable=False))
stores = table(
    "stores",
    identity(),
    C("merchant_id", String(64), ForeignKey("merchants.id"), nullable=False),
    C("name", String(120), nullable=False),
    C("timezone", String(80), nullable=False),
    C("demo", Boolean, nullable=False),
)
users = table(
    "users",
    identity(),
    C("username", String(120), nullable=False, unique=True),
    C("password_hash", Text, nullable=False),
)
memberships = table(
    "memberships",
    C("user_id", String(64), ForeignKey("users.id"), primary_key=True),
    C("store_id", String(64), ForeignKey("stores.id"), primary_key=True),
    C("role", String(20), nullable=False),
    Check("role IN ('owner','staff','viewer')", name="membership_role"),
)
sessions = table(
    "sessions",
    identity(),
    C("token_hash", String(64), unique=True, nullable=False),
    C("csrf_hash", String(64), nullable=False),
    C("user_id", String(64), nullable=False),
    scoped(),
    instant("expires_at"),
    ForeignKeyConstraint(["user_id", "store_id"], ["memberships.user_id", "memberships.store_id"]),
)
operations = table(
    "idempotency_operations",
    identity(),
    scoped(),
    C("actor_id", String(64), ForeignKey("users.id"), nullable=False),
    C("operation_key", String(100), nullable=False),
    C("request_digest", String(64), nullable=False),
    C("response", JSONB, nullable=False),
    C("status_code", Integer, nullable=False),
    instant("at"),
    U("store_id", "operation_key"),
)
