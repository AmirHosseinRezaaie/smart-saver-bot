"""baseline: initial empty migration to prove the pipeline

This migration intentionally makes no schema changes. Phase 2 builds
backend infrastructure, not business models (see
docs/architecture-decisions.md, ADR-009) — its purpose is only to
prove that `alembic upgrade head` / `alembic downgrade base` work
end-to-end against a real PostgreSQL database, via
`app.database.base.Base.metadata`. The first business model
(Phase 3+) will be the first migration with real `op.*` calls.

Revision ID: b9a2079e6af1
Revises:
Create Date: 2026-09-24 09:05:54.738059
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b9a2079e6af1"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. No-op: Phase 2 has no business models yet."""


def downgrade() -> None:
    """Downgrade schema. No-op: Phase 2 has no business models yet."""
