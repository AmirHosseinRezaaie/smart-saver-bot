import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# `Base.metadata` is the shared root every ORM model attaches to (see
# app/database/base.py); autogenerate discovers new models through it
# automatically as later phases add them. There is nothing registered
# on it yet in Phase 2 — see docs/architecture-decisions.md, ADR-009.
target_metadata = Base.metadata

# The connection string is never read from alembic.ini or hardcoded
# here. It comes from the same `Settings` the application itself uses
# (DATABASE_URL via environment variables / .env), so there is exactly
# one source of truth for it project-wide — see
# docs/architecture-decisions.md, ADR-010. This intentionally
# overrides whatever (unset) sqlalchemy.url is in alembic.ini.
_settings = get_settings()
if _settings.database_url:
    # Alembic's sync migration runner needs a sync-style URL; strip an
    # async driver qualifier (e.g. "+asyncpg") if present so the same
    # DATABASE_URL value works for both the application (async) and
    # Alembic (async engine wrapped in a sync-compatible run, below).
    config.set_main_option("sqlalchemy.url", _settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
