"""Keep manually recorded noncash receipts out of the cash-drawer balance."""

from alembic import op
import sqlalchemy as sa

revision = "19b0c9cc7712"
down_revision = "0c7a1193f001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "business_entries",
        sa.Column("payment_channel", sa.String(12), server_default="cash", nullable=False),
    )
    op.create_check_constraint(
        "business_entry_channel",
        "business_entries",
        "payment_channel IN ('cash','bank','upi','other')",
    )


def downgrade():
    op.drop_constraint("business_entry_channel", "business_entries", type_="check")
    op.drop_column("business_entries", "payment_channel")
