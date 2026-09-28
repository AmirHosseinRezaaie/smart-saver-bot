"""Optional on-disk storage of raw provider responses (project document,
Phase 3: "Raw Snapshot"), kept for debugging and for spotting upstream
format changes.

Only the response body is stored — never request or response headers,
which is where cookies and tokens would live. The directory is listed in
`.gitignore`; snapshots must never be committed.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_NAME_PART = 80


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _safe_part(value: str) -> str:
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", value).strip("._")[:_MAX_NAME_PART]
    return cleaned or "unknown"


class RawSnapshotStore:
    def __init__(
        self,
        directory: Path,
        *,
        enabled: bool,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._directory = directory
        self._enabled = enabled
        self._clock = clock

    def save(self, operation: str, key: str, body: bytes) -> Path | None:
        """Write `body` to `<timestamp>_<operation>_<key>.json`.

        Returns the written path, or `None` when snapshots are disabled or
        the write failed. A failed write is logged and never raised: a
        debugging aid must not take down data acquisition.
        """

        if not self._enabled:
            return None

        timestamp = self._clock().strftime("%Y%m%dT%H%M%S%fZ")
        filename = f"{timestamp}_{_safe_part(operation)}_{_safe_part(key)}.json"
        path = self._directory / filename
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        except OSError:
            logger.warning("Could not write raw snapshot %s", filename, exc_info=True)
            return None
        return path
