"""Protect reviewed manual financial history and saved campaign drafts."""

from alembic import op

revision = "0c7a1193f001"
down_revision = "82c5f712ac4d"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("business_entries", "business_campaigns"):
        op.execute(
            f"CREATE TRIGGER {name}_immutable BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()"
        )


def downgrade():
    for name in ("business_entries", "business_campaigns"):
        op.execute(f"DROP TRIGGER {name}_immutable ON {name}")
