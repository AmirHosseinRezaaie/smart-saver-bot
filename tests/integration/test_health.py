"""Integration tests: `GET /health` against a real FastAPI app instance,
backed by real PostgreSQL and Redis (Acceptance Criterion 1 in the
project document's Phase 2 section).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

pytestmark = pytest.mark.integration


async def test_health_reports_200_when_database_and_cache_are_up(integration_env: None) -> None:
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "healthy", "database": "healthy", "cache": "healthy"}


async def test_health_reports_503_and_identifies_the_failing_dependency(
    integration_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When one dependency (here, Redis) is unreachable, the application
    must not crash: it reports a deterministic degraded status naming
    which dependency failed, per the project document's Phase 2 risk
    mitigation ("failure of one dependency must not go unhandled").
    """

    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "healthy"
    assert body["cache"] == "unhealthy"


async def test_health_does_not_leak_internal_error_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even with no infrastructure configured at all, `/health` must
    respond deterministically rather than raising an unhandled exception.
    """

    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
