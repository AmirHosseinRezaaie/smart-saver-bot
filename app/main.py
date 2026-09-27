"""Application entry point.

Phase 2 scope: application composition only. `create_app()` builds a
real, runnable FastAPI application — registering the API router,
centralized exception handlers, and infrastructure lifecycle — and
nothing else. Business logic (search, basket optimization, the Bale
bot, ...) is introduced in later phases behind this same composition
root, per `app/api/router.py`'s docstring.

Import-time never opens a database or Redis connection (see
docs/architecture-decisions.md, ADR-007): `app = create_app()` below
only builds Python objects. Connections are opened in the `lifespan`
context manager, which FastAPI runs at actual process startup.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.database import close_redis, dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifecycle hook.

    Startup does not eagerly open connections either — PostgreSQL and
    Redis clients are still built lazily on first use (by
    `get_engine()` / `get_redis_client()`), so a `/health` call is what
    actually establishes the first connection. Shutdown, however, does
    need to be explicit: it releases whatever connections were opened
    during the process's lifetime so the process can exit cleanly.
    """

    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()


def main() -> None:  # pragma: no cover - exercised via `uvicorn`, not pytest
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=get_settings().debug)


if __name__ == "__main__":
    main()
