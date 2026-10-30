import os
from alembic import context
from backend.db import engine
from backend.models import metadata


def include_object(obj, name, kind, reflected, compare_to):
    # Search-path reflection aliases the selected schema to None. The Alembic
    # bookkeeping table is migration-owned, never an application table to drop.
    return not (kind == "table" and name == "alembic_version")


with engine().connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=metadata,
        compare_type=True,
        include_object=include_object,
        version_table_schema=os.getenv("DATABASE_SCHEMA", "public"),
    )
    with context.begin_transaction():
        context.run_migrations()
