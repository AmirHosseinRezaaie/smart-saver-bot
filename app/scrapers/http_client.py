"""Bounded, polite HTTP GET used by provider adapters.

Wraps an `httpx.AsyncClient` with three guarantees the project document
asks of the Data Provider layer: an explicit timeout (set on the client
by the caller), a small fixed number of attempts with exponential
backoff, and a minimum delay between requests. Only transient failures
are retried; permanent client errors fail immediately. Every failure
leaves this module as a `Provider*Exception`, so callers never see
`httpx` types.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping

import httpx

from app.core.exceptions import (
    ProviderException,
    ProviderNotFoundException,
    ProviderUnavailableException,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
_HTTP_NOT_FOUND = 404

QueryParams = Mapping[str, str | int]


class BoundedHttpClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        max_attempts: int,
        backoff_seconds: float,
        min_interval_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._min_interval_seconds = min_interval_seconds
        self._sleep = sleep
        self._monotonic = monotonic
        self._throttle_lock = asyncio.Lock()
        self._last_request_at: float | None = None

    async def get(self, path: str, params: QueryParams | None = None) -> bytes:
        """GET `path` (relative to the client's base URL) and return the body."""

        reason = ""
        last_error: httpx.TransportError | None = None
        for attempt in range(1, self._max_attempts + 1):
            await self._throttle()
            try:
                response = await self._client.get(path, params=params)
            except httpx.TransportError as exc:
                last_error = exc
                reason = type(exc).__name__
            except httpx.HTTPError as exc:
                raise ProviderException(
                    "The OKALA provider request could not be completed."
                ) from exc
            else:
                if response.is_success:
                    return response.content
                self._raise_for_permanent_status(response.status_code)
                last_error = None
                reason = f"HTTP {response.status_code}"

            if attempt < self._max_attempts:
                delay = self._backoff_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "OKALA provider attempt %d/%d failed (%s); retrying in %.2fs",
                    attempt,
                    self._max_attempts,
                    reason,
                    delay,
                )
                await self._sleep(delay)

        raise ProviderUnavailableException(
            f"The OKALA provider was unavailable after {self._max_attempts} attempts ({reason})."
        ) from last_error

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _raise_for_permanent_status(status_code: int) -> None:
        if status_code in _RETRYABLE_STATUS_CODES:
            return
        if status_code == _HTTP_NOT_FOUND:
            raise ProviderNotFoundException("The OKALA provider has no such resource.")
        raise ProviderException(f"The OKALA provider rejected the request (HTTP {status_code}).")

    async def _throttle(self) -> None:
        async with self._throttle_lock:
            if self._min_interval_seconds > 0 and self._last_request_at is not None:
                wait = self._min_interval_seconds - (self._monotonic() - self._last_request_at)
                if wait > 0:
                    await self._sleep(wait)
            self._last_request_at = self._monotonic()
