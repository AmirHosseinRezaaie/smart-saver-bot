"""Health-check endpoint.

`GET /health` reports whether the application itself is up and
whether it can currently reach PostgreSQL and Redis. It performs a
real connectivity check against each dependency (see
`app.database.check_database` / `app.database.check_redis`) rather
than returning a hardcoded `{"status": "ok"}` — a failing dependency
is reported, not hidden, and never raises an unhandled exception back
through this endpoint.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Response, status

from app.database import check_database, check_redis
from app.schemas.health import ComponentStatus, HealthResponse

router = APIRouter(tags=["health"])


def _component_status(is_healthy: bool) -> ComponentStatus:
    return "healthy" if is_healthy else "unhealthy"


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    """Report application, database, and cache health.

    Returns HTTP 200 when every dependency is healthy, HTTP 503 when
    any dependency is unhealthy. The body always reports per-component
    status regardless of the overall HTTP status code, so a caller can
    tell *which* dependency is degraded.
    """

    database_ok, cache_ok = await asyncio.gather(check_database(), check_redis())
    overall_healthy = database_ok and cache_ok

    response.status_code = (
        status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        database=_component_status(database_ok),
        cache=_component_status(cache_ok),
    )
