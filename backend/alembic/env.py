from logging.config import fileConfig
import os
import sys

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------
# Make backend importable
# ---------------------------------------------------------------------

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
        )
    ),
)

# ---------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------

load_dotenv()

config = context.config

database_url = os.getenv("DATABASE_URL")

# Railway/PostgreSQL deployments use psycopg v3. Normalize SQLAlchemy URLs
# so Alembic never falls back to the psycopg2 dialect.
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)

if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set."
    )

config.set_main_option(
    "sqlalchemy.url",
    database_url,
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------
# Import ALL models
# ---------------------------------------------------------------------

import app.models  # noqa: F401

from app.models.base import Base

target_metadata = Base.metadata


# ---------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------
# Online migrations
# ---------------------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()