"""Integration tests: application ↔ SQLAlchemy Async ↔ PostgreSQL.

These require a real, running PostgreSQL instance reachable at
`tests.conftest.TEST_DATABASE_URL` (see README.md → "Integration
Testing" for how to provide one locally or via CI services). They are
marked `integration` so they can be selected/deselected independently
of the unit suite, but nothing here mocks PostgreSQL — that is
precisely the "do not mock the integration" case the project document
calls out.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.database.session import check_database, get_engine, get_session_factory

pytestmark = pytest.mark.integration


async def test_check_database_succeeds_against_real_postgres(integration_env: None) -> None:
    assert await check_database() is True


async def test_engine_executes_a_real_query(integration_env: None) -> None:
    engine = get_engine()

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS value"))
        row = result.one()

    assert row.value == 1


async def test_session_factory_round_trips_a_value(integration_env: None) -> None:
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await session.execute(text("SELECT 2 + 2 AS total"))
        assert result.scalar_one() == 4


async def test_check_database_fails_fast_against_unreachable_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreachable database is reported as unhealthy, not raised, and
    the check honors its timeout instead of hanging.
    """

    # Port 1 is a reserved, never-listening port — connection refused
    # is effectively immediate, keeping the test fast while still
    # exercising the real failure path (as opposed to a DNS timeout,
    # which would be slow and environment-dependent).
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://ssb:********@localhost:1/nope")
    from app.core.config import get_settings

    get_settings.cache_clear()

    assert await check_database(timeout=2.0) is False
