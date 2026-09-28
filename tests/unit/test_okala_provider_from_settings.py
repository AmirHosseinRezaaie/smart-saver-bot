"""Unit test for `OkalaProvider.from_settings` configuration wiring.

Verifies the provider fails fast (project document, chapter 11: fail
loudly on misconfiguration) rather than silently defaulting to some
guessed OKALA host when unconfigured.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import ConfigurationException
from app.scrapers.okala_provider import OkalaProvider


def test_from_settings_raises_when_base_url_missing() -> None:
    settings = Settings(_env_file=None, okala_provider_base_url=None)  # type: ignore[call-arg]

    with pytest.raises(ConfigurationException):
        OkalaProvider.from_settings(settings)


async def test_from_settings_builds_a_working_provider() -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, okala_provider_base_url="https://provider.test"
    )

    provider = OkalaProvider.from_settings(settings)

    assert provider is not None
    await provider.aclose()
