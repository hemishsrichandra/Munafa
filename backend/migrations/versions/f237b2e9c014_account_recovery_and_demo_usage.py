"""Hashed one-time account recovery and bounded public-demo provider usage."""

from alembic import op
import sqlalchemy as sa

revision = "f237b2e9c014"
down_revision = "19b0c9cc7712"
branch_labels = None
depends_on = None


def upgrade():
    # Existing accounts fail closed until explicitly approved; do not infer provenance.
    op.add_column(
        "users",
        sa.Column("provider_access", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "account_recovery_codes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("expires_at > created_at", name="recovery_expiry"),
    )
    op.create_index("ix_account_recovery_codes_user_id", "account_recovery_codes", ["user_id"])
    op.create_table(
        "service_usage_counters",
        sa.Column("scope", sa.String(100), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("reserved_paise", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("calls >= 0 AND reserved_paise >= 0", name="usage_nonnegative"),
    )
    op.create_table(
        "service_usage_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("actor_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("reserved_paise", sa.BigInteger(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reserved_paise > 0", name="usage_reservation_positive"),
    )
    op.create_index("ix_service_usage_events_store_id", "service_usage_events", ["store_id"])
    op.execute(
        "CREATE TRIGGER service_usage_events_immutable BEFORE UPDATE OR DELETE ON service_usage_events FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()"
    )


def downgrade():
    # Only rehearsal on disposable schemas is automated. Never downgrade populated app data.
    op.drop_table("service_usage_events")
    op.drop_table("service_usage_counters")
    op.drop_table("account_recovery_codes")
    op.drop_column("users", "provider_access")
