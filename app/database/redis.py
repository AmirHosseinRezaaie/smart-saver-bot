"""Async Redis client management.

Mirrors `app/database/session.py`'s pattern: a single process-wide
client, built lazily from `Settings.redis_url`, with a small health
check used by the `/health` endpoint. No caching business logic lives
here yet — this is cache *infrastructure* only (see
docs/architecture-decisions.md, ADR-008).
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.exceptions import CacheException

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the process-wide async Redis client, creating it on first use."""

    global _client
    if _client is None:
        settings = get_settings()
        if not settings.redis_url:
            raise CacheException("REDIS_URL is not configured.")

        _client = redis.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_timeout,
            socket_connect_timeout=settings.redis_timeout,
            decode_responses=True,
        )
    return _client


async def get_redis() -> redis.Redis:
    """FastAPI dependency yielding the shared Redis client.

    Usage in a future endpoint:

        @router.get("/cached-thing")
        async def cached_thing(client: redis.Redis = Depends(get_redis)):
            ...
    """

    return get_redis_client()


async def close_redis() -> None:
    """Close the shared Redis client. Called from the app's shutdown hook."""

    global _client
    if _client is not None:
        await _client.aclose()
    _client = None


async def check_redis(timeout: float | None = None) -> bool:
    """Ping Redis to verify connectivity.

    Returns `True` if Redis answered within `timeout` seconds, `False`
    otherwise. Never raises — the caller (the health endpoint) treats
    a `False` as a reportable-but-non-crashing failure.
    """

    settings = get_settings()
    effective_timeout = timeout if timeout is not None else settings.redis_timeout

    if not settings.redis_url:
        return False

    try:
        client = get_redis_client()
        await asyncio.wait_for(client.ping(), timeout=effective_timeout)
        return True
    except (TimeoutError, RedisError, OSError, CacheException):
        logger.warning("Redis health check failed.", exc_info=True)
        return False
