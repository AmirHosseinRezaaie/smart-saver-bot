"""Initial catalog synchronization from `OkalaProviderInterface` into the
local database (project document, chapter 13, Phase 4, task 42).

Fetches categories and products exclusively through the existing provider
abstraction — this module never talks HTTP and knows nothing about
schema.org/JSON-LD; see `app.scrapers.interfaces.OkalaProviderInterface`.
Manual/explicit execution is sufficient for this phase (project document:
"Sync Job اولیه، اجرای دستی در این فاز"); real scheduling is Phase 8's
"Background Jobs" deliverable and is deliberately not built here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import product_repository as repo
from app.schemas.okala import RawProduct
from app.scrapers.interfaces import OkalaProviderInterface
from app.utils.persian_normalizer import normalize_text

logger = logging.getLogger(__name__)

DEFAULT_STORE_NAME = "OKALA"


@dataclass
class CatalogSyncResult:
    """Outcome of one `CatalogSyncService.sync()` run."""

    categories_synced: int = 0
    products_created: int = 0
    products_updated: int = 0
    products_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def products_synced(self) -> int:
        return self.products_created + self.products_updated


class CatalogSyncService:
    """Populates `Store`/`Category`/`Product`/`Price`/`Discount` from a provider.

    Safe to run more than once: products are upserted by
    `(store_id, external_id)` rather than re-inserted (see
    `product_repository.upsert_product`), and each run appends a fresh
    `Price` (and `Discount`, if present) snapshot — that repetition is
    intentional price *history* (chapter 7.1), not a duplication bug.

    One malformed product never aborts the whole sync: it is logged,
    counted in `CatalogSyncResult.products_skipped`/`errors`, and the sync
    continues with the next product (Phase 4 "Data Consistency": optional
    provider fields being unavailable must not fail the sync).
    """

    def __init__(
        self,
        provider: OkalaProviderInterface,
        session: AsyncSession,
        *,
        store_name: str = DEFAULT_STORE_NAME,
    ) -> None:
        self._provider = provider
        self._session = session
        self._store_name = store_name

    async def sync(self) -> CatalogSyncResult:
        result = CatalogSyncResult()
        store = await repo.get_or_create_store(self._session, self._store_name)

        categories = await self._provider.fetch_categories()
        category_id_by_external_id: dict[str, int] = {}
        for category in categories:
            row = await repo.get_or_create_category(
                self._session, external_id=category.external_id, name=category.name
            )
            category_id_by_external_id[category.external_id] = row.id
            result.categories_synced += 1

        for category in categories:
            await self._sync_category_products(
                store_id=store.id,
                category_external_id=category.external_id,
                category_id=category_id_by_external_id.get(category.external_id),
                result=result,
            )

        return result

    async def _sync_category_products(
        self,
        *,
        store_id: int,
        category_external_id: str,
        category_id: int | None,
        result: CatalogSyncResult,
    ) -> None:
        page = 1
        while True:
            products = await self._provider.fetch_products(category_external_id, page=page)
            if not products:
                break
            for raw in products:
                await self._sync_one_product(
                    store_id=store_id, category_id=category_id, raw=raw, result=result
                )
            page += 1

    async def _sync_one_product(
        self,
        *,
        store_id: int,
        category_id: int | None,
        raw: RawProduct,
        result: CatalogSyncResult,
    ) -> None:
        try:
            is_new = (
                await repo.get_product_by_external_id(
                    self._session, store_id=store_id, external_id=raw.external_id
                )
                is None
            )
            product = await repo.upsert_product(
                self._session,
                store_id=store_id,
                external_id=raw.external_id,
                name=raw.name,
                normalized_name=normalize_text(raw.name),
                category_id=category_id,
            )

            if raw.original_price is not None or raw.final_price is not None:
                await repo.add_price(
                    self._session,
                    product_id=product.id,
                    original_price=raw.original_price,
                    final_price=raw.final_price,
                    discount=_compute_discount(raw.original_price, raw.final_price),
                )

            if is_new:
                result.products_created += 1
            else:
                result.products_updated += 1
        except Exception as exc:  # noqa: BLE001 - one bad product must not abort the sync
            logger.warning(
                "Skipping product %r during catalog sync", raw.external_id, exc_info=True
            )
            result.products_skipped += 1
            result.errors.append(f"{raw.external_id}: {exc}")


def _compute_discount(
    original_price: int | None, final_price: int | None
) -> tuple[int, float] | None:
    """Derive `(amount, percent)` from a price pair, or `None` if there is
    no real discount to record (either price missing, or `final >= original`,
    which `app.schemas.okala.RawProduct` already guarantees cannot happen
    the other way around)."""

    if original_price is None or final_price is None:
        return None
    if original_price <= 0 or final_price >= original_price:
        return None

    amount = original_price - final_price
    percent = round((amount / original_price) * 100, 2)
    return amount, percent
