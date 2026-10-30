"""PostgreSQL schema. Alembic owns DDL; the application never creates tables."""

from sqlalchemy import (
    MetaData,
    Table,
    Column as C,
    String,
    Text,
    Boolean,
    Integer,
    BigInteger,
    Numeric,
    Date,
    DateTime,
    LargeBinary,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint as U,
    CheckConstraint as Check,
    Index,
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
suppliers = table(
    "suppliers",
    identity(),
    scoped(),
    C("name", String(100), nullable=False),
    C("name_key", String(100), nullable=False),
    C("phone", String(16), nullable=False),
    U("store_id", "name_key"),
    owned_unique(),
)
cases = table(
    "cases",
    identity(),
    scoped(),
    C("synthetic", Boolean, nullable=False),
    C("status", String(20), nullable=False),
    C("version", Integer, nullable=False),
    instant("created_at"),
    C("delivery_complete", Boolean, nullable=False),
    C("pricing_confirmed", Boolean, nullable=False),
    C("approved_version", Integer),
    C("approved_amount_paise", BigInteger),
    C("follow_up", Date),
    C("promise", Text),
    C("attachment_id", String(64)),
    owned_unique(),
    Check("version > 0", name="case_version"),
    Check("approved_amount_paise IS NULL OR approved_amount_paise > 0", name="case_amount"),
    Check(
        "status IN ('review','ready','sent','promised','partial','resolved')", name="case_status"
    ),
)
invoices = table(
    "invoices",
    identity(),
    scoped(),
    C("case_id", String(64), nullable=False),
    C("supplier_id", String(64), nullable=False),
    C("supplier_name", String(100), nullable=False),
    C("supplier_phone", String(16), nullable=False),
    C("reference", String(60), nullable=False),
    C("reference_key", String(60), nullable=False),
    C("date", Date, nullable=False),
    C("pricing_note", Text, nullable=False),
    owned("case_id", "cases"),
    owned("supplier_id", "suppliers"),
    owned_unique(),
    U("store_id", "case_id"),
    U("store_id", "supplier_id", "reference_key"),
)
invoice_lines = table(
    "invoice_lines",
    identity(),
    scoped(),
    C("invoice_id", String(64), nullable=False),
    C("position", Integer, nullable=False),
    C("name", String(120), nullable=False),
    C("billed", Numeric(20, 6), nullable=False),
    C("received", Numeric(20, 6)),
    C("unit", String(12), nullable=False),
    C("received_unit", String(12), nullable=False),
    C("unit_confirmed", Boolean, nullable=False),
    C("price_paise", BigInteger, nullable=False),
    C("note", Text, nullable=False),
    owned("invoice_id", "invoices"),
    Check("billed > 0 AND billed <= 100000", name="line_billed"),
    Check("received IS NULL OR (received >= 0 AND received <= 100000)", name="line_received"),
    Check("price_paise > 0 AND price_paise <= 100000000", name="line_price"),
    U("store_id", "invoice_id", "position"),
)
attachments = table(
    "attachments",
    identity(),
    scoped(),
    C("case_id", String(64), nullable=False),
    C("name", String(200), nullable=False),
    C("mime", String(80), nullable=False),
    C("data", LargeBinary, nullable=False),
    C("digest", String(64), nullable=False),
    C("synthetic_fields", JSONB),
    instant("created_at"),
    owned("case_id", "cases"),
    owned_unique(),
    Check("octet_length(data) > 0 AND octet_length(data) <= 8388608", name="attachment_size"),
)
resolutions = table(
    "resolutions",
    identity(),
    scoped(),
    C("case_id", String(64), nullable=False),
    C("supplier_id", String(64), nullable=False),
    C("kind", String(10), nullable=False),
    C("evidence_reference", String(100), nullable=False),
    C("reference_key", String(100), nullable=False),
    C("amount_paise", BigInteger, nullable=False),
    C("attachment_id", String(64), nullable=False),
    C("proof_digest", String(64), nullable=False),
    instant("at"),
    owned("case_id", "cases"),
    owned("supplier_id", "suppliers"),
    owned("attachment_id", "attachments"),
    owned_unique(),
    U("store_id", "supplier_id", "reference_key"),
    U("store_id", "supplier_id", "proof_digest"),
    Check("amount_paise > 0", name="resolution_amount"),
    Check("kind IN ('credit','refund')", name="resolution_kind"),
)
audit_events = table(
    "audit_events",
    identity(),
    scoped(),
    C("entity_id", String(64), nullable=False),
    C("entity_type", String(40), nullable=False),
    C("actor_id", String(64), ForeignKey("users.id"), nullable=False),
    C("action", String(80), nullable=False),
    C("prior_version", Integer),
    C("new_version", Integer),
    C("source_ids", JSONB, nullable=False),
    C("detail", Text, nullable=False),
    C("snapshot", JSONB),
    instant("at"),
    Index("ix_audit_entity", "store_id", "entity_id", "at"),
)
financial_events = table(
    "financial_events",
    identity(),
    scoped(),
    C("case_id", String(64), nullable=False),
    C("resolution_id", String(64), nullable=False),
    C("amount_paise", BigInteger, nullable=False),
    instant("at"),
    owned("case_id", "cases"),
    owned("resolution_id", "resolutions"),
    U("store_id", "resolution_id"),
    Check("amount_paise > 0", name="financial_amount"),
)
actions = table(
    "assistant_actions",
    identity(),
    scoped(),
    C("action_type", String(40), nullable=False),
    C("entity_id", String(64), nullable=False),
    C("payload", JSONB, nullable=False),
    C("payload_digest", String(64), nullable=False),
    C("risk_level", String(12), nullable=False),
    C("source_ids", JSONB, nullable=False),
    C("status", String(20), nullable=False),
    C("version", Integer, nullable=False),
    C("expected_version", Integer, nullable=False),
    C("idempotency_key", String(100), nullable=False),
    C("created_by", String(64), ForeignKey("users.id"), nullable=False),
    C("approved_by", String(64), ForeignKey("users.id")),
    C("approved_at", DateTime(timezone=True)),
    C("approved_digest", String(64)),
    C("expires_at", DateTime(timezone=True), nullable=False),
    owned_unique(),
    U("store_id", "idempotency_key"),
    Check("status IN ('proposed','approved','executed','expired')", name="action_status"),
    Check("version > 0", name="action_version"),
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
