"""Keep invoice supplier wording separate from mutable supplier directory labels."""

from alembic import op
import sqlalchemy as sa

revision = "37c45f100e71"
down_revision = "2a6b45d80201"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("supplier_name", sa.String(100), nullable=True))
    op.add_column("invoices", sa.Column("supplier_phone", sa.String(16), nullable=True))
    op.execute(
        "UPDATE invoices SET supplier_name=suppliers.name, supplier_phone=suppliers.phone FROM suppliers WHERE invoices.supplier_id=suppliers.id AND invoices.store_id=suppliers.store_id"
    )
    op.alter_column("invoices", "supplier_name", nullable=False)
    op.alter_column("invoices", "supplier_phone", nullable=False)


def downgrade():
    # Retaining source identity is intentional: this downgrade requires owner approval/backup.
    op.drop_column("invoices", "supplier_phone")
    op.drop_column("invoices", "supplier_name")
