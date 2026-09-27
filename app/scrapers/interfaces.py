"""The contract between the Service layer and any OKALA data source.

Nothing here mentions HTTP, HTML, or any client library: swapping the
concrete adapter (feed, official API, ...) must leave every caller
untouched. Implementations translate their own failures into the
`Provider*Exception` family from `app.core.exceptions`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.okala import Category, RawProduct, RawProductDetail


class OkalaProviderInterface(ABC):
    @abstractmethod
    async def fetch_categories(self) -> list[Category]:
        """Return all categories; an empty list means the source has none."""

    @abstractmethod
    async def fetch_products(self, category_id: str, page: int = 1) -> list[RawProduct]:
        """Return one page (1-based) of a category's products.

        An empty list means the page is past the end of the category.
        """

    @abstractmethod
    async def fetch_product_detail(self, product_id: str) -> RawProductDetail:
        """Return one product's detail.

        Raises `ProviderNotFoundException` if the product does not exist.
        """
