"""Concrete `OkalaProviderInterface` adapter.

## Access method (see `docs/okala-research.md` for the full investigation)

At the time this was written, no documented official OKALA API or data
feed could be confirmed, and this environment's own tooling refused to
fetch `okala.com` on robots-exclusion grounds — so the live site itself
could not be sampled to confirm its markup. Per the project document's
guidance (chapter 10.1) and the "never fabricate a working adapter"
policy, this adapter is therefore built against the standard, publicly
documented `schema.org/Product` structured-data contract that many
storefronts embed in their product and category pages, rather than
against any OKALA-specific endpoint or HTML structure that could not be
verified. `okala_provider_base_url` has **no default** (see
`app/core/config.py`); nothing here calls a hardcoded OKALA host.

This keeps the adapter fully testable (see `tests/unit/test_okala_provider.py`)
while leaving explicit TODOs — flagged below and in the research doc — for
the one thing that still requires a human to confirm against the live
site (or an official OKALA contact) before this adapter is pointed at
production: whether OKALA's pages actually carry this markup, and if so
its exact field names.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationException,
    ProviderInvalidResponseException,
    ProviderNotFoundException,
)
from app.schemas.okala import Category, RawProduct, RawProductDetail
from app.scrapers.http_client import BoundedHttpClient
from app.scrapers.interfaces import OkalaProviderInterface
from app.scrapers.jsonld import extract_jsonld_blocks, find_by_type
from app.scrapers.mapping import map_category, map_product, map_product_detail
from app.scrapers.snapshot import RawSnapshotStore

logger = logging.getLogger(__name__)

# TODO(Phase 3 follow-up, see docs/okala-research.md #3):
# confirm against the live site (or an official OKALA developer contact)
# that these are in fact the schema.org types/paths OKALA uses, and adjust
# `_CATEGORY_PAGE_PATH` / `_PRODUCT_LIST_PATH` / `_PRODUCT_DETAIL_PATH`
# and the `@type` names below accordingly. Nothing below is a confirmed
# OKALA endpoint.
_CATEGORY_PAGE_PATH = "/"
_PRODUCT_LIST_PATH_TEMPLATE = "/category/{category_id}"
_PRODUCT_DETAIL_PATH_TEMPLATE = "/product/{product_id}"
_CATEGORY_TYPES = ("CollectionPage", "Category")
_PRODUCT_TYPE = "Product"


class OkalaProvider(OkalaProviderInterface):
    def __init__(
        self,
        http_client: BoundedHttpClient,
        *,
        snapshot_store: RawSnapshotStore | None = None,
    ) -> None:
        self._http = http_client
        self._snapshots = snapshot_store

    @classmethod
    def from_settings(cls, settings: Settings) -> OkalaProvider:
        if not settings.okala_provider_base_url:
            raise ConfigurationException(
                "OKALA_PROVIDER_BASE_URL is not configured; see docs/okala-research.md "
                "for the access method that must be confirmed before setting it."
            )
        client = httpx.AsyncClient(
            base_url=settings.okala_provider_base_url,
            timeout=settings.okala_request_timeout,
            headers={"User-Agent": settings.okala_user_agent},
        )
        http_client = BoundedHttpClient(
            client,
            max_attempts=settings.okala_max_attempts,
            backoff_seconds=settings.okala_retry_backoff,
            min_interval_seconds=settings.okala_min_request_interval,
        )
        snapshots = RawSnapshotStore(
            Path(settings.okala_snapshot_dir), enabled=settings.okala_snapshot_enabled
        )
        return cls(http_client, snapshot_store=snapshots)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def fetch_categories(self) -> list[Category]:
        body = await self._http.get(_CATEGORY_PAGE_PATH)
        self._snapshot("fetch_categories", "index", body)
        blocks = self._parse_jsonld(body, context="category index")

        categories: list[Category] = []
        for node in find_by_type(blocks, _CATEGORY_TYPES[0]) + find_by_type(
            blocks, _CATEGORY_TYPES[1]
        ):
            try:
                categories.append(map_category(node))
            except ValueError:
                logger.warning("Skipping malformed category node", exc_info=True)
        return categories

    async def fetch_products(self, category_id: str, page: int = 1) -> list[RawProduct]:
        path = _PRODUCT_LIST_PATH_TEMPLATE.format(category_id=category_id)
        body = await self._http.get(path, params={"page": page})
        self._snapshot("fetch_products", f"{category_id}_p{page}", body)
        blocks = self._parse_jsonld(body, context=f"category {category_id!r} page {page}")

        products: list[RawProduct] = []
        for node in find_by_type(blocks, _PRODUCT_TYPE):
            try:
                products.append(map_product(node, category_external_id=category_id))
            except ValueError:
                logger.warning("Skipping malformed product node", exc_info=True)
        return products

    async def fetch_product_detail(self, product_id: str) -> RawProductDetail:
        path = _PRODUCT_DETAIL_PATH_TEMPLATE.format(product_id=product_id)
        body = await self._http.get(path)
        self._snapshot("fetch_product_detail", product_id, body)
        blocks = self._parse_jsonld(body, context=f"product {product_id!r}")

        products = find_by_type(blocks, _PRODUCT_TYPE)
        if not products:
            raise ProviderNotFoundException(f"OKALA product {product_id!r} was not found.")
        try:
            return map_product_detail(products[0])
        except ValueError as exc:
            raise ProviderInvalidResponseException(
                f"OKALA product {product_id!r} had an unexpected response structure."
            ) from exc

    def _parse_jsonld(self, body: bytes, *, context: str) -> list[dict[str, Any]]:
        if not body:
            raise ProviderInvalidResponseException(
                f"OKALA returned an empty response for {context}."
            )
        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProviderInvalidResponseException(
                f"OKALA response for {context} was not valid UTF-8 text."
            ) from exc
        blocks = extract_jsonld_blocks(html)
        if not blocks:
            raise ProviderInvalidResponseException(
                f"OKALA response for {context} had no structured product data."
            )
        return blocks

    def _snapshot(self, operation: str, key: str, body: bytes) -> None:
        if self._snapshots is not None:
            self._snapshots.save(operation, key, body)
