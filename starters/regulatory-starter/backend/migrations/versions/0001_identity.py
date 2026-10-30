"""Inherited identity, session and request-idempotency foundation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "foundation_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "merchants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
    )
    op.create_table(
        "stores",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("merchant_id", sa.String(64), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("demo", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(120), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.CheckConstraint("role IN ('owner','staff','viewer')", name="membership_role"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "store_id"], ["memberships.user_id", "memberships.store_id"]
        ),
    )
    op.create_index("ix_sessions_store_id", "sessions", ["store_id"])
    op.create_table(
        "idempotency_operations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("actor_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("operation_key", sa.String(100), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("response", JSONB(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "operation_key"),
    )
    op.create_index("ix_idempotency_operations_store_id", "idempotency_operations", ["store_id"])


def downgrade():
    # On populated environments: verify backup, show plan and get owner approval.
    for name in [
        "idempotency_operations",
        "sessions",
        "memberships",
        "users",
        "stores",
        "merchants",
    ]:
        op.drop_table(name)
