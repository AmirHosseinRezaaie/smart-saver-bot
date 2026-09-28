"""Persistence models.

Every ORM model must be imported here so it registers on
`app.database.base.Base.metadata` and Alembic's autogenerate can discover
it (see `app/database/base.py`). `Product`/`Store`/`Category`/`Price`/
`Discount` land in Phase 4 (see `app/models/catalog.py`); `User`, `Basket`,
and the rest of chapter 7's entities remain reserved for later phases.
"""

from app.models.catalog import Category, Discount, Price, Product, Store

__all__ = ["Category", "Discount", "Price", "Product", "Store"]
