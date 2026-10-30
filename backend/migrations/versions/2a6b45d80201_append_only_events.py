"""Enforce immutable financial evidence and expose rebuildable recovery projection."""

from alembic import op

revision = "2a6b45d80201"
down_revision = "8eb2b55dbe9b"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE FUNCTION reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Append-only record cannot be updated or deleted'; END; $$""")
    for name in ("audit_events", "financial_events", "resolutions"):
        op.execute(
            f"CREATE TRIGGER {name}_immutable BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()"
        )
    op.execute(
        "CREATE VIEW case_recovery_balances AS SELECT store_id, case_id, SUM(amount_paise)::BIGINT AS recovered_paise FROM financial_events GROUP BY store_id, case_id"
    )


def downgrade():
    op.execute("DROP VIEW case_recovery_balances")
    for name in ("audit_events", "financial_events", "resolutions"):
        op.execute(f"DROP TRIGGER {name}_immutable ON {name}")
    op.execute("DROP FUNCTION reject_immutable_change()")
