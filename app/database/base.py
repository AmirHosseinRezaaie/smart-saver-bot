"""Shared SQLAlchemy declarative base.

Every ORM model added in later phases (`User`, `Product`, `Store`,
`Price`, `Discount`, `Basket`, ...) inherits from `Base` so Alembic's
autogenerate can discover them all from a single import root
(`app.database.base.Base.metadata`).

Phase 2 intentionally defines no business models here — see
docs/architecture-decisions.md, ADR-009. This module exists purely as
the shared metadata root that those future models attach to.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
