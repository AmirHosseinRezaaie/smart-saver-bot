"""Smoke tests for Phase 1.

These tests only prove the application is importable, its
configuration loads, and it constructs without raising. They must
never touch the network, OKALA, Bale, PostgreSQL, or Redis — Phase 1
has no business logic to test yet (see docs/architecture-decisions.md,
ADR-005).
"""

from __future__ import annotations

import importlib

import pytest

from app.core.config import ConfigError, Settings, get_settings, load_settings
from app.main import build_app


def test_app_package_is_importable() -> None:
    """The top-level application package imports without side effects."""

    module = importlib.import_module("app")
    assert module is not None


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configuration is read from environment variables, not hardcoded."""

    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.delenv("BALE_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = load_settings()

    assert isinstance(settings, Settings)
    assert settings.environment == "testing"
    assert settings.bale_bot_token is None
    assert settings.is_production is False


def test_settings_rejects_invalid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unrecognized ENVIRONMENT value fails fast and loudly."""

    monkeypatch.setenv("ENVIRONMENT", "not-a-real-environment")

    with pytest.raises(ConfigError):
        load_settings()


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """`get_settings` caches within a process."""

    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "development")

    first = get_settings()
    second = get_settings()

    assert first is second
    get_settings.cache_clear()


def test_application_builds_without_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """The application constructs end-to-end with no external service."""

    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "development")

    settings = build_app()

    assert isinstance(settings, Settings)
    get_settings.cache_clear()
