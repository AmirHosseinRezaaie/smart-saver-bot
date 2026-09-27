"""Unit tests for `app.scrapers.mapping` and `app.scrapers.jsonld`.

Pure functions over fixed JSON-LD fixtures — no network involved, per
the project document's Phase 3 "Test" requirement.
"""

from __future__ import annotations

import pytest

from app.scrapers.jsonld import extract_jsonld_blocks, find_by_type
from app.scrapers.mapping import map_category, map_product, map_product_detail

_PRODUCT_HTML = """
<html><head>
<script type="application/ld+json">
{"@type": "Product", "sku": "SKU-1", "name": "Basmati Rice 1kg",
 "offers": {"@type": "Offer", "price": "150000", "availability": "https://schema.org/InStock",
            "seller": {"name": "OKALA"}}}
</script>
</head></html>
"""


def test_extract_jsonld_blocks_parses_valid_script() -> None:
    blocks = extract_jsonld_blocks(_PRODUCT_HTML)
    assert len(blocks) == 1
    assert blocks[0]["name"] == "Basmati Rice 1kg"


def test_extract_jsonld_blocks_ignores_malformed_script() -> None:
    html = '<script type="application/ld+json">{not valid json</script>'
    assert extract_jsonld_blocks(html) == []


def test_extract_jsonld_blocks_flattens_graph() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@graph": [{"@type": "Product", "name": "A"}, {"@type": "Product", "name": "B"}]}'
        "</script>"
    )
    blocks = extract_jsonld_blocks(html)
    assert [b["name"] for b in blocks] == ["A", "B"]


def test_extract_jsonld_blocks_empty_for_no_scripts() -> None:
    assert extract_jsonld_blocks("<html><body>no data here</body></html>") == []


def test_find_by_type_filters_on_at_type() -> None:
    blocks = [{"@type": "Product", "name": "A"}, {"@type": "Category", "name": "B"}]
    assert [b["name"] for b in find_by_type(blocks, "Product")] == ["A"]


def test_map_category_from_minimal_node() -> None:
    category = map_category({"name": "لبنیات", "identifier": "dairy"})
    assert category.external_id == "dairy"
    assert category.name == "لبنیات"
    assert category.parent_external_id is None


def test_map_category_missing_name_raises() -> None:
    with pytest.raises(ValueError, match="malformed category"):
        map_category({"identifier": "dairy"})


def test_map_product_full_fields() -> None:
    node = {
        "sku": "SKU-1",
        "name": "Basmati Rice 1kg",
        "highPrice": "200000",
        "url": "https://example.com/p/1",
        "offers": {"price": "150000", "availability": "https://schema.org/InStock"},
    }
    product = map_product(node, category_external_id="rice")
    assert product.external_id == "SKU-1"
    assert product.original_price == 200000
    assert product.final_price == 150000
    assert product.in_stock is True
    assert product.category_external_id == "rice"


def test_map_product_missing_optional_fields_does_not_crash() -> None:
    product = map_product({"sku": "SKU-2", "name": "Mystery Item"})
    assert product.original_price is None
    assert product.final_price is None
    assert product.in_stock is None
    assert product.url is None


def test_map_product_out_of_stock() -> None:
    node = {
        "sku": "SKU-3",
        "name": "Sold Out Item",
        "offers": {"price": "1000", "availability": "https://schema.org/OutOfStock"},
    }
    assert map_product(node).in_stock is False


def test_map_product_missing_identity_raises() -> None:
    with pytest.raises(ValueError, match="malformed product"):
        map_product({"name": "No id or sku"})


def test_map_product_final_price_above_original_raises() -> None:
    node = {
        "sku": "SKU-4",
        "name": "Inconsistent Item",
        "highPrice": "1000",
        "offers": {"price": "2000"},
    }
    with pytest.raises(ValueError, match="malformed product"):
        map_product(node)


def test_map_product_detail_includes_store_name() -> None:
    node = {
        "sku": "SKU-5",
        "name": "Detailed Item",
        "offers": {"price": "5000", "seller": {"name": "OKALA"}},
    }
    detail = map_product_detail(node)
    assert detail.store_name == "OKALA"
    assert detail.final_price == 5000


def test_map_product_detail_missing_store_name_raises() -> None:
    node = {"sku": "SKU-6", "name": "No Store Item", "offers": {"price": "5000"}}
    with pytest.raises(ValueError, match="missing seller/brand name"):
        map_product_detail(node)


def test_map_product_detail_falls_back_to_brand_name() -> None:
    node = {
        "sku": "SKU-7",
        "name": "Branded Item",
        "brand": {"name": "Some Brand"},
        "offers": {"price": "5000"},
    }
    assert map_product_detail(node).store_name == "Some Brand"
