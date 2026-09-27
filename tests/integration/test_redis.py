"""Integration tests: application ↔ async Redis client ↔ Redis.

Require a real, running Redis instance reachable at
`tests.conftest.TEST_REDIS_URL` (see README.md → "Integration
Testing"). Uses a dedicated Redis logical database (`/15`) and cleans
up every key it writes, so it never collides with development data.
"""

from __future__ import annotations

import pytest

from app.database.redis import check_redis, get_redis_client

pytestmark = pytest.mark.integration


async def test_check_redis_succeeds_against_real_redis(integration_env: None) -> None:
    assert await check_redis() is True


async def test_redis_set_get_delete_round_trip(integration_env: None) -> None:
    client = get_redis_client()
    key = "smart-saver-bot:test:round-trip"

    try:
        await client.set(key, "value", ex=30)
        assert await client.get(key) == "value"
    finally:
        await client.delete(key)

    assert await client.get(key) is None


async def test_check_redis_fails_fast_against_unreachable_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    assert await check_redis(timeout=2.0) is False
