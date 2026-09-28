"""Async SQLAlchemy engine and session management.

This module is the single place a SQLAlchemy `AsyncEngine` is
constructed for the whole application — nothing else builds its own
engine (see docs/architecture-decisions.md, ADR-007). Import time
never touches the network: the engine is created lazily, and the
first real connection attempt only happens when something (a request,
a health check, a test) actually needs one.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.exceptions import DatabaseException

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(settings: Settings) -> AsyncEngine:
    if not settings.database_url:
        raise DatabaseException("DATABASE_URL is not configured.")

    # pool_pre_ping guards against connections that went stale while
    # idle (e.g. a database restart or a cloud provider's idle-connection
    # reaper) by issuing a lightweight liveness check before handing a
    # pooled connection back out, at the cost of one extra round trip
    # per checkout.
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
        echo=False,
    )


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""

    global _engine
    if _engine is None:
        _engine = _build_engine(get_settings())
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """Open an `AsyncSession`, commit on success, and always close it.

    Any exception rolls the transaction back before propagating, so a
    failed request never leaves a dangling transaction on the
    connection before it is returned to the pool.
    """

    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped `AsyncSession`.

    Usage in a future endpoint:

        @router.get("/products")
        async def list_products(session: AsyncSession = Depends(get_db_session)):
            ...

    Repositories in later phases receive this same session rather than
    opening their own, keeping transaction boundaries at the request
    layer.
    """

    async with session_scope() as session:
        yield session


async def dispose_engine() -> None:
    """Close all pooled connections. Called from the app's shutdown hook."""

    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def reset_engine_for_tests() -> None:
    """Drop any cached engine/session factory so the next call to
    `get_engine()`/`get_session_factory()` rebuilds from current settings.

    Used by tests that change `DATABASE_URL` between cases; production
    code never needs this.
    """

    await dispose_engine()


async def check_database(timeout: float | None = None) -> bool:
    """Run a trivial `SELECT 1` to verify PostgreSQL connectivity.

    Returns `True` if the database answered within `timeout` seconds,
    `False` otherwise. Never raises — callers (the health endpoint)
    treat a `False` as a reportable-but-non-crashing failure rather
    than an unhandled exception.
    """

    settings = get_settings()
    effective_timeout = timeout if timeout is not None else settings.database_pool_timeout

    if not settings.database_url:
        return False

    try:
        engine = get_engine()

        async def _ping() -> None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_ping(), timeout=effective_timeout)
        return True
    except (TimeoutError, SQLAlchemyError, OSError):
        logger.warning("Database health check failed.", exc_info=True)
        return False
