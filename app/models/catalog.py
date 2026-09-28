"""ORM entities for the product catalog (project document, chapter 7).

Only the subset of chapter 7's entity list that Phase 4 (product
processing, normalization and search) actually needs is implemented here:
`Store`, `Category`, `Product`, `Price`, `Discount`. The remaining chapter 7
entities (`User`, `Basket`, `BasketItem`, `SearchHistory`, `Favorite`,
`PriceAlert`, `ShoppingList`, `Notification`) depend on the bot/user layer
(Phase 5+) or are explicitly scheduled for Phase 8 ("تکمیل مدل‌های باقیمانده
... SearchHistory کامل") in the project document's own phase table, so they
are intentionally not added yet — see docs/architecture-decisions.md,
ADR-009 for the same reasoning applied to earlier phases.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Store(Base):
    """A supported storefront (OKALA today; others in the future)."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="store")


class Category(Base):
    """A product category, used for grouping and (in a later phase) basket weighting."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # `external_id` is not part of chapter 7's documented field list, but
    # is the minimum addition needed to idempotently match a provider
    # category across sync runs (Phase 4, task 42: "update existing ...
    # rather than blindly creating duplicates"). Nullable so a category
    # created some other way (e.g. manually, in a later phase) stays valid.
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_default: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """A normalized catalog product belonging to exactly one store."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "external_id", name="uq_products_store_id_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    # The normalized-search phrase (project document, chapter 10.3): the
    # output of `app.utils.persian_normalizer.normalize_text(name)`,
    # persisted so the fuzzy-search index (see the Phase 4 Alembic
    # migration) never has to normalize at query time.
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    store: Mapped[Store] = relationship(back_populates="products")
    category: Mapped[Category | None] = relationship(back_populates="products")
    prices: Mapped[list["Price"]] = relationship(
        back_populates="product",
        order_by="Price.fetched_at.desc()",
        cascade="all, delete-orphan",
    )


class Price(Base):
    """One price snapshot for a product (history, not just "latest") — chapter 7.1."""

    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    # Nullable: the provider does not always expose either price (project
    # document, Phase 4 "Data Consistency" — never fabricate a missing
    # value), matching `app.schemas.okala.RawProduct`.
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    product: Mapped[Product] = relationship(back_populates="prices")
    discount: Mapped["Discount | None"] = relationship(
        back_populates="price", uselist=False, cascade="all, delete-orphan"
    )


class Discount(Base):
    """Discount details for exactly one price record (chapter 7.2: 1-to-1, optional)."""

    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_id: Mapped[int] = mapped_column(
        ForeignKey("prices.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    percent: Mapped[float] = mapped_column(Float, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    price: Mapped[Price] = relationship(back_populates="discount")
