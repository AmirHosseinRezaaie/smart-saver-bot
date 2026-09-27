"""Response schema for the `/health` endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ComponentStatus = Literal["healthy", "unhealthy"]
OverallStatus = Literal["healthy", "degraded"]


class HealthResponse(BaseModel):
    """Structured, machine-readable health status.

    `status` is `"healthy"` only when every checked dependency is
    healthy; otherwise it is `"degraded"` and the per-component fields
    say which one is failing. The HTTP status code always stays 200 —
    dependency health is reported in the body, not signaled by making
    the health check itself fail (see `app/api/health.py`).
    """

    status: OverallStatus
    database: ComponentStatus
    cache: ComponentStatus
