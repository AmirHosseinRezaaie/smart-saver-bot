"""Unit tests for `app.scrapers.http_client.BoundedHttpClient`.

Every test drives an `httpx.AsyncClient` wired to `httpx.MockTransport`,
so no real network call is ever made. `sleep` is replaced by a no-op that
records how it was called, so retry/backoff behavior is verified without
actually waiting.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import (
    ProviderException,
    ProviderNotFoundException,
    ProviderUnavailableException,
)
from app.scrapers.http_client import BoundedHttpClient


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0.01,
    min_interval_seconds: float = 0.0,
) -> tuple[BoundedHttpClient, list[float]]:
    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport, base_url="https://provider.test")
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = BoundedHttpClient(
        async_client,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        min_interval_seconds=min_interval_seconds,
        sleep=fake_sleep,
    )
    return client, sleeps


async def test_get_returns_body_on_first_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ok")

    client, sleeps = _make_client(handler)
    assert await client.get("/x") == b"ok"
    assert sleeps == []
    await client.aclose()


async def test_get_retries_transient_failure_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, content=b"ok")

    client, sleeps = _make_client(handler, max_attempts=3)
    assert await client.get("/x") == b"ok"
    assert calls["count"] == 3
    assert len(sleeps) == 2
    assert sleeps[1] > sleeps[0]  # exponential backoff
    await client.aclose()


async def test_get_exhausts_retries_and_raises_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client, sleeps = _make_client(handler, max_attempts=3)
    with pytest.raises(ProviderUnavailableException):
        await client.get("/x")
    assert len(sleeps) == 2  # no sleep after the final attempt
    await client.aclose()


async def test_get_does_not_retry_permanent_client_error() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(400)

    client, sleeps = _make_client(handler, max_attempts=3)
    with pytest.raises(ProviderException):
        await client.get("/x")
    assert calls["count"] == 1
    assert sleeps == []
    await client.aclose()


async def test_get_raises_not_found_on_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client, _ = _make_client(handler, max_attempts=3)
    with pytest.raises(ProviderNotFoundException):
        await client.get("/x")
    await client.aclose()


async def test_get_retries_connection_failure() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, content=b"ok")

    client, sleeps = _make_client(handler, max_attempts=3)
    assert await client.get("/x") == b"ok"
    assert len(sleeps) == 1
    await client.aclose()


async def test_get_raises_unavailable_after_repeated_timeouts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client, _ = _make_client(handler, max_attempts=2)
    with pytest.raises(ProviderUnavailableException):
        await client.get("/x")
    await client.aclose()


async def test_min_request_interval_is_respected() -> None:
    clock = _FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ok")

    client, sleeps = _make_client(handler, min_interval_seconds=2.0)
    client._monotonic = clock  # type: ignore[assignment]

    await client.get("/x")
    clock.value += 0.5  # less than the 2s minimum interval
    await client.get("/x")

    assert sleeps and sleeps[0] == pytest.approx(1.5)
    await client.aclose()
