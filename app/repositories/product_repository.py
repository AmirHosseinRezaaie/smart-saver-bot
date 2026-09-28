"""Product persistence and search primitives (project document, chapter 7 / 13).

Every PostgreSQL-specific concern — `pg_trgm` functions, eager-loading
strategy, upsert semantics — lives here. `SearchService` and
`CatalogSyncService` never construct SQL themselves; this is the "keep
database/search concerns inside the appropriate layer" boundary the Phase 4
brief calls for.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Category, Discount, Price, Product, Store


def _product_query():
    """Base SELECT for `Product`, with the relationships callers need
    already eagerly loaded so returned rows stay usable after the session
    that fetched them is closed (e.g. across a request boundary)."""

    return select(Product).options(
        selectinload(Product.store),
        selectinload(Product.category),
        selectinload(Product.prices).selectinload(Price.discount),
    )


# --- Search --------------------------------------------------------------


async def find_by_normalized_name(session: AsyncSession, normalized_name: str) -> list[Product]:
    """Exact match against `Product.normalized_name` (search stage 1)."""

    stmt = _product_query().where(Product.normalized_name == normalized_name)
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


async def find_by_similarity(
    session: AsyncSession,
    normalized_query: str,
    *,
    threshold: float,
    limit: int,
) -> list[Product]:
    """Trigram fuzzy match against `Product.normalized_name` (search stage 2).

    Uses `pg_trgm`'s `word_similarity(query, name)` rather than plain
    `similarity(query, name)`: `word_similarity` scores the
    best-matching *substring* of `name` against `query`, so a short query
    fully contained in a longer product name (e.g. "رب گوجه" inside "رب
    گوجه فرنگی") is not unfairly penalized for the length difference the
    way symmetric `similarity` would penalize it. That is exactly the
    Phase 4 acceptance criterion.
    """

    score = func.word_similarity(normalized_query, Product.normalized_name)
    stmt = (
        _product_query()
        .where(score >= threshold)
        .order_by(score.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


# --- Store / Category upserts (used by catalog sync) ----------------------


async def get_or_create_store(
    session: AsyncSession, name: str, *, base_url: str | None = None
) -> Store:
    result = await session.execute(select(Store).where(Store.name == name))
    store = result.scalar_one_or_none()
    if store is not None:
        return store

    store = Store(name=name, base_url=base_url, is_active=True)
    session.add(store)
    await session.flush()
    return store


async def get_or_create_category(
    session: AsyncSession, *, external_id: str, name: str
) -> Category:
    result = await session.execute(select(Category).where(Category.external_id == external_id))
    category = result.scalar_one_or_none()
    if category is not None:
        if category.name != name:
            category.name = name
        return category

    category = Category(external_id=external_id, name=name)
    session.add(category)
    await session.flush()
    return category


# --- Product / Price / Discount upserts (used by catalog sync) ------------


async def get_product_by_external_id(
    session: AsyncSession, *, store_id: int, external_id: str
) -> Product | None:
    result = await session.execute(
        select(Product).where(Product.store_id == store_id, Product.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def upsert_product(
    session: AsyncSession,
    *,
    store_id: int,
    external_id: str,
    name: str,
    normalized_name: str,
    category_id: int | None,
) -> Product:
    """Create the product if it's new, or update its mutable fields if not.

    Matches by `(store_id, external_id)` — the provider's own identifier —
    so re-running a sync never creates a duplicate row for the same
    product (project document, Phase 4, task 42).
    """

    product = await get_product_by_external_id(session, store_id=store_id, external_id=external_id)
    if product is None:
        product = Product(
            store_id=store_id,
            external_id=external_id,
            name=name,
            normalized_name=normalized_name,
            category_id=category_id,
        )
        session.add(product)
    else:
        product.name = name
        product.normalized_name = normalized_name
        product.category_id = category_id

    await session.flush()
    return product


async def add_price(
    session: AsyncSession,
    *,
    product_id: int,
    original_price: int | None,
    final_price: int | None,
    discount: tuple[int, float] | None = None,
    fetched_at: datetime | None = None,
) -> Price:
    """Append a new price snapshot for a product.

    Intentionally always inserts rather than updating an existing row:
    `Price` is a history table (chapter 7.1: "آخرین قیمت/تاریخچه"), so each
    sync run recording a fresh snapshot — even an unchanged one — is
    correct, not a duplication bug.
    """

    price = Price(
        product_id=product_id,
        original_price=original_price,
        final_price=final_price,
        **({"fetched_at": fetched_at} if fetched_at is not None else {}),
    )
    session.add(price)
    await session.flush()

    if discount is not None:
        amount, percent = discount
        session.add(Discount(price_id=price.id, amount=amount, percent=percent))
        await session.flush()

    return price
