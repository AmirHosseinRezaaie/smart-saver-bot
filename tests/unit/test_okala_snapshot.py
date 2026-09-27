"""Unit tests for `app.scrapers.snapshot.RawSnapshotStore`.

Covers the project document's Phase 3 "Raw Snapshot" requirement:
enabled, disabled, and a filesystem failure, all without touching a
real snapshot directory outside of pytest's `tmp_path`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.scrapers.snapshot import RawSnapshotStore


def _fixed_clock() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_save_writes_file_when_enabled(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path, enabled=True, clock=_fixed_clock)

    path = store.save("fetch_categories", "index", b'{"ok": true}')

    assert path is not None
    assert path.read_bytes() == b'{"ok": true}'
    assert path.parent == tmp_path


def test_save_does_nothing_when_disabled(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path, enabled=False, clock=_fixed_clock)

    assert store.save("fetch_categories", "index", b"data") is None
    assert list(tmp_path.iterdir()) == []


def test_save_sanitizes_unsafe_key(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path, enabled=True, clock=_fixed_clock)

    path = store.save("fetch_product_detail", "../../etc/passwd", b"data")

    assert path is not None
    assert path.parent == tmp_path
    assert ".." not in path.name


def test_save_returns_none_on_filesystem_failure(tmp_path: Path) -> None:
    # Point the store at a path that cannot be created as a directory
    # (its parent is a file, not a directory), so `mkdir` raises.
    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("x")
    store = RawSnapshotStore(blocking_file / "nested", enabled=True, clock=_fixed_clock)

    assert store.save("fetch_categories", "index", b"data") is None
