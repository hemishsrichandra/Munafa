"""One PostgreSQL/SQLAlchemy access path. No startup DDL and no database fallback."""

import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def database_url():
    value = os.environ.get("DATABASE_URL", "")
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value[len("postgres://"):]
    elif value.startswith("postgresql://") and not value.startswith("postgresql+psycopg://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    if not value or make_url(value).drivername != "postgresql+psycopg":
        raise RuntimeError(
            "DATABASE_URL must use postgresql+psycopg. No database fallback is available."
        )
    return value


@lru_cache(maxsize=4)
def engine_for(url, schema):
    if schema and not schema.replace("_", "").isalnum():
        raise RuntimeError("Invalid PostgreSQL schema")
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema}"} if schema else {},
    )


def engine():
    return engine_for(database_url(), os.getenv("DATABASE_SCHEMA", "public"))
