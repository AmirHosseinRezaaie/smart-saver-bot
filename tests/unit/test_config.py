"""Unit tests for `app.core.config`.

None of these touch the network, PostgreSQL, or Redis — they only
exercise environment-variable parsing and Pydantic validation, per the
project document's five required configuration test cases (Phase 2,
"Configuration Tests").
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_valid_environment_loads_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 1: a valid ENVIRONMENT value loads settings without error."""

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.environment == "development"
    assert settings.is_production is False


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 2: an unrecognized ENVIRONMENT value fails validation."""

    monkeypatch.setenv("ENVIRONMENT", "not-a-real-environment")

    with pytest.raises(ValidationError):
        Settings()


def test_database_url_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 3: DATABASE_URL is read from the environment, not hardcoded."""

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:********@localhost:5432/shopping_bot")

    settings = get_settings()

    assert settings.database_url == "postgresql+asyncpg://user:********@localhost:5432/shopping_bot"


def test_redis_url_is_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 4: REDIS_URL is read from the environment, not hardcoded."""

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/3")

    settings = get_settings()

    assert settings.redis_url == "redis://localhost:6379/3"


def test_no_secret_literal_in_source_code() -> None:
    """Case 5: no field in `Settings` carries a non-empty default that looks
    like a real credential, and an unconfigured environment yields `None`
    for every secret-shaped field rather than a hardcoded fallback value.
    """

    source = inspect.getsource(Settings)
    forbidden_substrings = ["://user:", "://admin:", "password123", "changeme"]
    for forbidden in forbidden_substrings:
        assert forbidden not in source, f"Possible hardcoded credential literal: {forbidden!r}"

    # Constructing Settings with no relevant environment variables set
    # (achieved by pointing `_env_file` at a nonexistent path so no
    # local `.env` leaks in) must never fall back to a real value.
    bare = Settings(_env_file=None)  # type: ignore[call-arg]
    assert bare.bale_bot_token is None
    assert bare.database_url is None
    assert bare.redis_url is None


def test_production_environment_rejects_debug_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secure Configuration requirement: DEBUG must not be enabled in production."""

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError):
        Settings()


def test_production_environment_accepts_debug_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings()

    assert settings.is_production is True
    assert settings.debug is False


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """`get_settings` caches within a process."""

    monkeypatch.setenv("ENVIRONMENT", "development")

    first = get_settings()
    second = get_settings()

    assert first is second


def test_settings_is_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    settings = get_settings()

    with pytest.raises(ValidationError):
        settings.environment = "production"  # type: ignore[misc]
