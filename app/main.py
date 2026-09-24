"""Application entry point.

Phase 1 scope only: prove the application package imports, loads its
configuration, and starts up without error. This module intentionally
contains no business logic — the Bale bot, HTTP API, and background
workers are introduced in later phases (see docs/architecture-decisions.md).
"""

from __future__ import annotations

from app.core.config import Settings, get_settings


def build_app() -> Settings:
    """Construct the application's runtime configuration.

    Stands in for a real application factory (e.g. a FastAPI app or a
    Bale bot dispatcher) until those layers exist. Returning the
    loaded `Settings` lets the smoke test verify the whole import →
    configure → construct path with no external service required.
    """

    return get_settings()


def main() -> None:
    settings = build_app()
    print(f"Smart Saver Bot — environment: {settings.environment}")


if __name__ == "__main__":
    main()
