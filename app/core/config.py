"""Application configuration.

Reads all configuration exclusively from environment variables. No
secret or credential is ever hardcoded here — see docs/SECURITY.md.

Phase 1 note: this module intentionally depends on the standard
library only. Pydantic-based settings/validation is introduced in
Phase 2 alongside FastAPI (see docs/architecture-decisions.md,
ADR-004), since Phase 1 has no request/response boundary yet that
would need it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

_VALID_ENVIRONMENTS = frozenset({"development", "staging", "production", "testing"})


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings, sourced from environment variables.

    Every field is optional at the Python level because Phase 1 has no
    functionality that actually dials out to Bale, PostgreSQL, or
    Redis yet; a value being unset only becomes an error once a later
    phase's code path tries to use it. `environment` is the one field
    validated eagerly since it controls behavior (e.g. debug settings)
    from Phase 1 onward.
    """

    environment: str
    bale_bot_token: str | None
    database_url: str | None
    redis_url: str | None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_debug(self) -> bool:
        # Secure Configuration requirement (project doc, chapter 11):
        # debug/verbose error output must be disabled in production.
        return not self.is_production


def _read_environment_name(raw: str) -> str:
    normalized = raw.strip().lower()
    if normalized not in _VALID_ENVIRONMENTS:
        allowed = ", ".join(sorted(_VALID_ENVIRONMENTS))
        raise ConfigError(f"Invalid ENVIRONMENT={raw!r}. Expected one of: {allowed}")
    return normalized


def load_settings() -> Settings:
    """Build a `Settings` instance from the current process environment.

    Never raises for missing BALE_BOT_TOKEN / DATABASE_URL / REDIS_URL
    in Phase 1 — those are consumed by later phases. It does raise for
    an invalid ENVIRONMENT value, since that is meaningful today.
    """

    environment_raw = os.environ.get("ENVIRONMENT", "development")
    return Settings(
        environment=_read_environment_name(environment_raw),
        bale_bot_token=os.environ.get("BALE_BOT_TOKEN") or None,
        database_url=os.environ.get("DATABASE_URL") or None,
        redis_url=os.environ.get("REDIS_URL") or None,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor for application settings.

    Cached so the environment is parsed once per process rather than
    on every call site. Tests that need a fresh read can call
    `get_settings.cache_clear()` first.
    """

    return load_settings()
