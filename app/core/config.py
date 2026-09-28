"""Application configuration.

Reads all configuration exclusively from environment variables (or a
local `.env` file, for development) via Pydantic Settings. No secret
or credential is ever hardcoded here — see docs/SECURITY-relevant
notes in `docs/architecture-decisions.md`, ADR-006.

Phase 1 used a stdlib `dataclass` for this (see ADR-004). Phase 2
migrates to `pydantic-settings` now that FastAPI has landed and the
project has an actual request/response and infrastructure-config
boundary that benefits from Pydantic's validation. This module is the
single source of truth for configuration — nothing elsewhere reads
`os.environ` directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "testing"]


class Settings(BaseSettings):
    """Immutable, environment-driven application settings.

    Every field is read from an environment variable of the same
    (upper-cased) name, optionally via a local `.env` file. Field
    values are validated eagerly at construction time (i.e. at
    application startup), so a misconfigured deployment fails fast
    instead of failing later inside a request handler.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- Core -----------------------------------------------------------
    environment: Environment = "development"
    app_name: str = "Smart Saver Bot"
    app_version: str = "0.2.0-dev"
    debug: bool = True

    # --- Bale bot (Phase 5+) ---------------------------------------------
    # Not consumed by Backend Core itself; read here only so it has one
    # single, validated configuration source project-wide, per the
    # project document's "no parallel config systems" requirement.
    bale_bot_token: str | None = None

    # --- PostgreSQL -------------------------------------------------------
    database_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout: float = Field(default=30.0, gt=0)

    # --- Redis --------------------------------------------------------
    redis_url: str | None = None
    redis_timeout: float = Field(default=5.0, gt=0)

    # --- OKALA data provider (Phase 3) -----------------------------------
    # No default base URL on purpose: which endpoint is legally and
    # technically permitted is documented in docs/okala-research.md, and
    # an unset value must fail loudly instead of guessing a host.
    okala_provider_base_url: str | None = None
    okala_request_timeout: float = Field(default=10.0, gt=0)
    okala_max_attempts: int = Field(default=3, ge=1, le=5)
    okala_retry_backoff: float = Field(default=0.5, ge=0)
    okala_min_request_interval: float = Field(default=1.0, ge=0)
    okala_user_agent: str = "SmartSaverBot/0.3"
    okala_snapshot_enabled: bool = False
    okala_snapshot_dir: str = "raw_snapshots"

    # --- Product search (Phase 4) -----------------------------------------
    # Minimum pg_trgm similarity (0-1) a candidate must score to be
    # returned by fuzzy search. Configurable rather than hardcoded in
    # `app.repositories.product_repository` per the project document's
    # explicit "آستانه شباهت قابل‌تنظیم" (configurable similarity threshold)
    # requirement (Phase 4, task 43).
    search_similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    # Below this normalized-query length, fuzzy search is skipped entirely
    # rather than run with a threshold that can't discriminate a 1-character
    # query — the Phase 4 risk table's own mitigation ("تعیین حداقل طول
    # عبارت برای فعال‌سازی تطبیق فازی") for low-quality short-query matches.
    search_min_query_length: int = Field(default=2, ge=1)
    search_max_results: int = Field(default=20, ge=1, le=100)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> Settings:
        """Secure Configuration requirement (project doc, chapter 11):
        debug/verbose error output must be disabled in production.

        Rather than silently overriding a misconfigured `DEBUG=true` in
        production (which would hide the mistake), this fails startup
        loudly so the deployment is fixed before it ever serves traffic.
        """

        if self.is_production and self.debug:
            raise ValueError(
                "DEBUG must not be enabled when ENVIRONMENT=production. "
                "Set DEBUG=false (or unset it; it already defaults to a "
                "safe value everywhere except this check catching a "
                "misconfigured environment)."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor for application settings.

    Cached so the environment is parsed and validated once per
    process rather than on every call site (and, notably, once per
    FastAPI dependency injection rather than per request). Tests that
    need a fresh read after changing environment variables should call
    `get_settings.cache_clear()` first.
    """

    return Settings()
