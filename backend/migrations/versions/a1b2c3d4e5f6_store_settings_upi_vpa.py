"""Store settings: UPI VPA and reminder language preferences"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f237b2e9c014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "store_settings",
        sa.Column("store_id", sa.String(length=64), nullable=False),
        sa.Column("upi_vpa", sa.String(length=120), nullable=True),
        sa.Column("reminder_language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "reminder_language IN ('en','hi','kn')", name="settings_language"
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], name=op.f("fk_store_settings_store_id_stores")
        ),
        sa.PrimaryKeyConstraint("store_id", name=op.f("pk_store_settings")),
    )


def downgrade():
    op.drop_table("store_settings")
