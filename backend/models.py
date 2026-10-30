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

# Batch 5: accepted purchase/receiving evidence and append-only stock truth.
products = table(
    "products",
    identity(),
    scoped(),
    C("code", String(60), nullable=False),
    C("name", String(120), nullable=False),
    C("unit", String(12), nullable=False),
    C("barcode", String(80)),
    C("reorder_threshold", Numeric(20, 6)),
    C("expiry_tracking", Boolean, nullable=False),
    C("version", Integer, nullable=False),
    C("stock_version", Integer, nullable=False),
    instant("created_at"),
    owned_unique(),
    U("store_id", "code"),
    U("store_id", "barcode"),
    Check("unit IN ('piece','pack','carton','kg')", name="product_unit"),
    Check("reorder_threshold IS NULL OR reorder_threshold >= 0", name="product_threshold"),
    Check("version > 0 AND stock_version >= 0", name="product_version"),
)
conversions = table(
    "unit_conversions",
    identity(),
    scoped(),
    C("product_id", String(64), nullable=False),
    C("from_unit", String(12), nullable=False),
    C("to_unit", String(12), nullable=False),
    C("factor", Numeric(20, 6), nullable=False),
    C("provenance", String(300), nullable=False),
    C("created_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("created_at"),
    owned("product_id", "products"),
    owned_unique(),
    U("store_id", "product_id", "from_unit", "to_unit"),
    Check("factor > 0 AND factor <= 100000", name="conversion_factor"),
    Check(
        "from_unit <> to_unit AND from_unit IN ('piece','pack','carton','kg') AND to_unit IN ('piece','pack','carton','kg')",
        name="conversion_units",
    ),
)
purchases = table(
    "purchases",
    identity(),
    scoped(),
    C("case_id", String(64)),
    C("supplier_key", String(100)),
    C("reference_key", String(60)),
    C("status", String(16), nullable=False),
    C("version", Integer, nullable=False),
    C("draft", JSONB, nullable=False),
    C("delivery_complete", Boolean, nullable=False),
    C("source_kind", String(20), nullable=False),
    C("created_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("created_at"),
    owned("case_id", "cases"),
    owned_unique(),
    U("store_id", "case_id"),
    U("store_id", "supplier_key", "reference_key"),
    Check("status IN ('draft','accepted') AND version > 0", name="purchase_state"),
)
purchase_documents = table(
    "purchase_documents",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("name", String(200), nullable=False),
    C("mime", String(80), nullable=False),
    C("data", LargeBinary, nullable=False),
    C("sha256", String(64), nullable=False),
    instant("created_at"),
    owned("purchase_id", "purchases"),
    owned_unique(),
    Check("octet_length(data)>0 AND octet_length(data)<=8388608", name="purchase_document_size"),
)
purchase_revisions = table(
    "purchase_revisions",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("revision", Integer, nullable=False),
    C("snapshot", JSONB, nullable=False),
    C("provenance", JSONB, nullable=False),
    C("created_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("created_at"),
    owned("purchase_id", "purchases"),
    U("store_id", "purchase_id", "revision"),
    owned_unique(),
)
purchase_acceptances = table(
    "purchase_acceptances",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("action_id", String(64), nullable=False),
    C("version", Integer, nullable=False),
    C("snapshot", JSONB, nullable=False),
    C("payload_digest", String(64), nullable=False),
    C("total_paise", BigInteger, nullable=False),
    C("accepted_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("accepted_at"),
    owned("purchase_id", "purchases"),
    owned("action_id", "assistant_actions"),
    owned_unique(),
    U("store_id", "purchase_id"),
    Check("total_paise >= 0", name="purchase_total"),
)
purchase_lines = table(
    "purchase_lines",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("product_id", String(64), nullable=False),
    C("position", Integer, nullable=False),
    C("description", String(120), nullable=False),
    C("billed_quantity", Numeric(20, 6), nullable=False),
    C("unit", String(12), nullable=False),
    C("unit_price_paise", BigInteger, nullable=False),
    C("effective_price_paise", BigInteger, nullable=False),
    C("tax_paise", BigInteger),
    C("tax_rate", Numeric(10, 6)),
    owned("purchase_id", "purchases"),
    owned("product_id", "products"),
    owned_unique(),
    U("store_id", "purchase_id", "position"),
    Check(
        "billed_quantity>0 AND unit_price_paise>0 AND effective_price_paise>0",
        name="purchase_line_values",
    ),
    Check("tax_paise IS NULL OR tax_paise>=0", name="purchase_line_tax"),
)
receiving_drafts = table(
    "receiving_drafts",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("version", Integer, nullable=False),
    C("purchase_version", Integer, nullable=False),
    C("status", String(16), nullable=False),
    C("payload", JSONB, nullable=False),
    C("created_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("created_at"),
    owned("purchase_id", "purchases"),
    owned_unique(),
    Check("version>0 AND status IN ('draft','accepted')", name="receiving_draft_state"),
)
receipts = table(
    "receipts",
    identity(),
    scoped(),
    C("purchase_id", String(64), nullable=False),
    C("draft_id", String(64), nullable=False),
    C("purchase_version", Integer, nullable=False),
    C("delivery_complete", Boolean, nullable=False),
    C("payload", JSONB, nullable=False),
    C("action_id", String(64), nullable=False),
    C("operation_id", String(100), nullable=False),
    C("accepted_by", String(64), ForeignKey("users.id"), nullable=False),
    instant("accepted_at"),
    owned("purchase_id", "purchases"),
    owned("draft_id", "receiving_drafts"),
    owned("action_id", "assistant_actions"),
    owned_unique(),
    U("store_id", "draft_id"),
    U("store_id", "operation_id"),
)
inventory_sources = table(
    "inventory_sources",
    identity(),
    scoped(),
    C("product_id", String(64), nullable=False),
    C("source_type", String(24), nullable=False),
    C("source_entity_id", String(64), nullable=False),
    C("reference", String(100), nullable=False),
    C("occurred_on", Date, nullable=False),
    C("reason", String(500), nullable=False),
    C("case_id", String(64)),
    C("snapshot", JSONB, nullable=False),
    C("actor_id", String(64), ForeignKey("users.id"), nullable=False),
    instant("created_at"),
    owned("product_id", "products"),
    owned("case_id", "cases"),
    owned_unique(),
    U("store_id", "case_id", "product_id", "source_type"),
    U("store_id", "product_id", "source_type", "reference"),
    Check(
        "source_type IN ('receipt','sale','return_in','return_out','damage','count','reversal','shortage_correction')",
        name="inventory_source_type",
    ),
)
inventory_lots = table(
    "inventory_lots",
    identity(),
    scoped(),
    C("product_id", String(64), nullable=False),
    C("source_id", String(64), nullable=False),
    C("batch_reference", String(100)),
    C("expiry_date", Date),
    instant("created_at"),
    owned("product_id", "products"),
    owned("source_id", "inventory_sources"),
    owned_unique(),
)
receipt_lines = table(
    "receipt_lines",
    identity(),
    scoped(),
    C("receipt_id", String(64), nullable=False),
    C("purchase_line_id", String(64), nullable=False),
    C("product_id", String(64), nullable=False),
    C("quantity", Numeric(20, 6), nullable=False),
    C("damaged_quantity", Numeric(20, 6), nullable=False),
    C("invoice_quantity", Numeric(20, 6), nullable=False),
    C("stock_quantity", Numeric(20, 6), nullable=False),
    C("unit", String(12), nullable=False),
    C("note", String(500), nullable=False),
    C("conversion_ids", JSONB, nullable=False),
    C("lot_id", String(64)),
    owned("receipt_id", "receipts"),
    owned("purchase_line_id", "purchase_lines"),
    owned("product_id", "products"),
    owned("lot_id", "inventory_lots"),
    owned_unique(),
    U("store_id", "receipt_id", "purchase_line_id"),
    Check(
        "quantity>=0 AND damaged_quantity>=0 AND damaged_quantity<=quantity AND invoice_quantity>=0 AND stock_quantity>=0",
        name="receipt_quantities",
    ),
)
inventory_events = table(
    "inventory_events",
    identity(),
    scoped(),
    C("product_id", String(64), nullable=False),
    C("source_id", String(64), nullable=False),
    C("lot_id", String(64)),
    C("kind", String(24), nullable=False),
    C("quantity_delta", Numeric(20, 6), nullable=False),
    C("unit", String(12), nullable=False),
    C("operation_id", String(100), nullable=False),
    C("reversal_of", String(64)),
    C("prior_version", Integer, nullable=False),
    C("new_version", Integer, nullable=False),
    C("actor_id", String(64), ForeignKey("users.id"), nullable=False),
    instant("at"),
    owned("product_id", "products"),
    owned("source_id", "inventory_sources"),
    owned("lot_id", "inventory_lots"),
    owned("reversal_of", "inventory_events"),
    owned_unique(),
    U("store_id", "source_id"),
    U("store_id", "reversal_of"),
    U("store_id", "product_id", "new_version"),
    Check("new_version=prior_version+1 AND prior_version>=0", name="inventory_event_version"),
    Check("quantity_delta<>0 OR kind IN ('count','shortage_correction')", name="inventory_delta"),
    Check(
        "kind IN ('receipt','sale','return_in','return_out','damage','count','reversal','shortage_correction')",
        name="inventory_event_kind",
    ),
    Index("ix_inventory_product_time", "store_id", "product_id", "at"),
)

products.append_constraint(U("store_id", "id", "unit"))
inventory_sources.append_constraint(U("store_id", "id", "product_id", "source_type"))
inventory_lots.append_constraint(U("store_id", "id", "product_id"))
purchase_lines.append_constraint(U("store_id", "id", "product_id"))
inventory_events.append_constraint(
    ForeignKeyConstraint(
        ["store_id", "product_id", "unit"],
        ["products.store_id", "products.id", "products.unit"],
        name="fk_inventory_event_product_unit",
    )
)
inventory_events.append_constraint(
    ForeignKeyConstraint(
        ["store_id", "source_id", "product_id", "kind"],
        [
            "inventory_sources.store_id",
            "inventory_sources.id",
            "inventory_sources.product_id",
            "inventory_sources.source_type",
        ],
        name="fk_inventory_event_source_kind",
    )
)
inventory_events.append_constraint(
    ForeignKeyConstraint(
        ["store_id", "lot_id", "product_id"],
        ["inventory_lots.store_id", "inventory_lots.id", "inventory_lots.product_id"],
        name="fk_inventory_event_lot_product",
    )
)
receipt_lines.append_constraint(
    ForeignKeyConstraint(
        ["store_id", "purchase_line_id", "product_id"],
        ["purchase_lines.store_id", "purchase_lines.id", "purchase_lines.product_id"],
        name="fk_receipt_line_purchase_product",
    )
)
