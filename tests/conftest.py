"""Shared pytest fixtures.

Every test gets a clean `Settings` cache and a clean database
engine/session factory / Redis client before and after it runs, so
one test's environment-variable changes (or cached connections) can
never leak into the next test — a requirement called out explicitly
in the project document (Phase 2, "Tests must not depend on
production": deterministic, isolated, reproducible).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from app.core.config import get_settings
from app.database.redis import close_redis
from app.database.session import reset_engine_for_tests

#: Connection strings for the *test* PostgreSQL/Redis instances this
#: test session talks to. These are local, non-production, throwaway
#: services (see README.md → "Testing" for how to start them) — never
#: a real deployment's credentials.
TEST_DATABASE_URL = "postgresql+asyncpg://ssb:********@localhost:5432/shopping_bot_test"
TEST_REDIS_URL = "redis://localhost:6379/15"


@pytest.fixture(autouse=True)
def _isolated_settings_cache() -> AsyncGenerator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def _isolated_infrastructure_clients() -> AsyncGenerator[None]:
    """Reset the process-wide engine/session-factory/Redis-client singletons
    around every test so a test that points DATABASE_URL/REDIS_URL at a
    throwaway or unreachable target never poisons a later test's connection.
    """

    yield
    await reset_engine_for_tests()
    await close_redis()


@pytest.fixture
def integration_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the application at the local test PostgreSQL/Redis instances.

    Used only by tests under `tests/integration/`, which are marked
    `@pytest.mark.integration` and require these services to actually
    be running (see README.md → "Integration Testing").
    """

    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)
    monkeypatch.delenv("BALE_BOT_TOKEN", raising=False)
    get_settings.cache_clear()
