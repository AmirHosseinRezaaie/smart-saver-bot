"""Unit tests for `app.scrapers.okala_provider.OkalaProvider` and the
`OkalaProviderInterface` contract it implements.

All HTTP is mocked via `httpx.MockTransport`; no test in this module (or
anywhere else in the suite) makes a real request to OKALA or any other
external host, per the project document's Phase 3 "Test" requirement.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from app.core.exceptions import ProviderInvalidResponseException, ProviderNotFoundException
from app.scrapers.http_client import BoundedHttpClient
from app.scrapers.interfaces import OkalaProviderInterface
from app.scrapers.okala_provider import OkalaProvider
from app.scrapers.snapshot import RawSnapshotStore

_CATEGORY_HTML = """
<script type="application/ld+json">
{"@type": "CollectionPage", "name": "Dairy", "identifier": "dairy"}
</script>
"""

_PRODUCT_LIST_HTML = """
<script type="application/ld+json">
{"@type": "Product", "sku": "SKU-1", "name": "Milk 1L",
 "offers": {"price": "45000", "availability": "https://schema.org/InStock"}}
</script>
<script type="application/ld+json">
{"@type": "Product", "name": "Missing SKU And ID"}
</script>
"""

_PRODUCT_DETAIL_HTML = """
<script type="application/ld+json">
{"@type": "Product", "sku": "SKU-1", "name": "Milk 1L",
 "offers": {"price": "45000", "seller": {"name": "OKALA"}}}
</script>
"""


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    snapshot_store: RawSnapshotStore | None = None,
) -> OkalaProvider:
    async_client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://provider.test"
    )
    http_client = BoundedHttpClient(
        async_client, max_attempts=1, backoff_seconds=0.0, min_interval_seconds=0.0
    )
    return OkalaProvider(http_client, snapshot_store=snapshot_store)


def test_okala_provider_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        OkalaProviderInterface()  # type: ignore[abstract]


def test_okala_provider_implements_interface() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=b"<html></html>"))
    assert isinstance(provider, OkalaProviderInterface)


async def test_fetch_categories_valid_response() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=_CATEGORY_HTML.encode()))
    categories = await provider.fetch_categories()
    assert [c.external_id for c in categories] == ["dairy"]
    await provider.aclose()


async def test_fetch_categories_empty_response_raises_invalid() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=b""))
    with pytest.raises(ProviderInvalidResponseException):
        await provider.fetch_categories()
    await provider.aclose()


async def test_fetch_categories_malformed_html_raises_invalid() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=b"<html>no data</html>"))
    with pytest.raises(ProviderInvalidResponseException):
        await provider.fetch_categories()
    await provider.aclose()


async def test_fetch_products_valid_response_skips_malformed_item() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=_PRODUCT_LIST_HTML.encode()))
    products = await provider.fetch_products("dairy", page=1)
    assert [p.external_id for p in products] == ["SKU-1"]
    await provider.aclose()


async def test_fetch_products_passes_pagination_params() -> None:
    seen_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(request.url.params)
        return httpx.Response(200, content=_PRODUCT_LIST_HTML.encode())

    provider = _provider(handler)
    await provider.fetch_products("dairy", page=2)
    assert seen_params["page"] == "2"
    await provider.aclose()


async def test_fetch_products_missing_optional_fields_does_not_crash() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type": "Product", "sku": "SKU-9", "name": "Bare Item"}'
        "</script>"
    )
    provider = _provider(lambda request: httpx.Response(200, content=html.encode()))
    products = await provider.fetch_products("dairy")
    assert products[0].final_price is None
    assert products[0].in_stock is None
    await provider.aclose()


async def test_fetch_product_detail_valid_response() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=_PRODUCT_DETAIL_HTML.encode()))
    detail = await provider.fetch_product_detail("SKU-1")
    assert detail.store_name == "OKALA"
    assert detail.final_price == 45000
    await provider.aclose()


async def test_fetch_product_detail_not_found() -> None:
    provider = _provider(lambda request: httpx.Response(404))
    with pytest.raises(ProviderNotFoundException):
        await provider.fetch_product_detail("missing")
    await provider.aclose()


async def test_fetch_product_detail_malformed_response_raises_invalid() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type": "Product", "sku": "X", "name": "N"}'
        "</script>"
    )
    provider = _provider(lambda request: httpx.Response(200, content=html.encode()))
    with pytest.raises(ProviderInvalidResponseException):
        await provider.fetch_product_detail("X")  # no seller/brand name
    await provider.aclose()


async def test_fetch_product_detail_no_product_block_raises_not_found() -> None:
    provider = _provider(lambda request: httpx.Response(200, content=_CATEGORY_HTML.encode()))
    with pytest.raises(ProviderNotFoundException):
        await provider.fetch_product_detail("X")
    await provider.aclose()


async def test_snapshot_is_written_when_store_is_enabled(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path, enabled=True)
    provider = _provider(
        lambda request: httpx.Response(200, content=_PRODUCT_DETAIL_HTML.encode()),
        snapshot_store=store,
    )
    await provider.fetch_product_detail("SKU-1")
    assert any(tmp_path.iterdir())
    await provider.aclose()
