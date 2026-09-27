"""Mapping from `schema.org/Product` (and `Category`/`CollectionPage`) JSON-LD
nodes onto the provider's raw schemas (`app.schemas.okala`).

Every function here is pure and network-free, which is what makes it
testable with fixed fixtures (project document, Phase 3 "Test" requirement).
A malformed individual node is reported by raising `ValueError`; callers
that process a list of nodes decide whether to skip it or fail the batch.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas.okala import Category, RawProduct, RawProductDetail

_IN_STOCK_AVAILABILITY = {
    "https://schema.org/InStock",
    "http://schema.org/InStock",
    "InStock",
}
_OUT_OF_STOCK_AVAILABILITY = {
    "https://schema.org/OutOfStock",
    "http://schema.org/OutOfStock",
    "OutOfStock",
}


def _as_int_price(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _availability(offer: dict[str, Any]) -> bool | None:
    availability = offer.get("availability")
    if availability in _IN_STOCK_AVAILABILITY:
        return True
    if availability in _OUT_OF_STOCK_AVAILABILITY:
        return False
    return None


def map_category(node: dict[str, Any]) -> Category:
    """Map a `CollectionPage`/`ItemList`-style category node.

    Raises `ValueError` (via Pydantic) if required fields are missing.
    """

    try:
        return Category(
            external_id=str(node.get("identifier") or node.get("url") or node["name"]),
            name=str(node["name"]),
            parent_external_id=(
                str(node["parent_external_id"]) if node.get("parent_external_id") else None
            ),
        )
    except (KeyError, ValidationError) as exc:
        raise ValueError(f"malformed category node: {exc}") from exc


def map_product(node: dict[str, Any], *, category_external_id: str | None = None) -> RawProduct:
    """Map a `schema.org/Product` node from a category/listing page.

    Raises `ValueError` if the node lacks the fields a product needs
    (name and an identifier); price, stock, and URL are optional per the
    project document's "fields may be unavailable" requirement.
    """

    offers = node.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    try:
        return RawProduct(
            external_id=str(node.get("sku") or node.get("productID") or node["@id"]),
            name=str(node["name"]),
            category_external_id=category_external_id,
            original_price=_as_int_price(node.get("highPrice") or offers.get("highPrice")),
            final_price=_as_int_price(offers.get("price")),
            in_stock=_availability(offers),
            url=node.get("url") or offers.get("url"),
        )
    except (KeyError, ValidationError) as exc:
        raise ValueError(f"malformed product node: {exc}") from exc


def map_product_detail(node: dict[str, Any]) -> RawProductDetail:
    """Map a single product page's `schema.org/Product` node to full detail.

    Raises `ValueError` if the node is missing the store/brand name in
    addition to the requirements of `map_product`.
    """

    base = map_product(node)
    offers = node.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    seller = offers.get("seller") or {}
    brand = node.get("brand") or {}
    store_name = seller.get("name") or brand.get("name")
    if not store_name:
        raise ValueError("malformed product detail node: missing seller/brand name")

    return RawProductDetail(**base.model_dump(), store_name=str(store_name))
