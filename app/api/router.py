"""Top-level API router.

`app/main.py` includes exactly this one router, keeping route
registration out of `main.py` itself. Later phases add their own
routers here (e.g. a versioned `/api/v1` router for business
endpoints) without `main.py` needing to change — see
docs/architecture-decisions.md, ADR-006.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
