"""Extraction of `schema.org` JSON-LD blocks (`<script type="application/ld+json">`)
from an HTML page.

The project document (chapter 10.1) identifies embedded structured data as the
most stable non-API way to read a product page, ahead of parsing raw HTML.
This module only extracts the *candidate* JSON blocks; interpreting their
contents as a Category/Product is `app.scrapers.mapping`'s job.
"""

from __future__ import annotations

import json
import re
from typing import Any

_SCRIPT_BLOCK = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_jsonld_blocks(html: str) -> list[dict[str, Any]]:
    """Return every parseable JSON-LD object found in `html`.

    A block that is not valid JSON is skipped rather than raised, since one
    unrelated (e.g. analytics) block on the page must not fail the whole
    page; the caller decides what to do if the list ends up empty.
    A `@graph` wrapper is flattened to its member nodes.
    """

    blocks: list[dict[str, Any]] = []
    for match in _SCRIPT_BLOCK.finditer(html):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in parsed if isinstance(parsed, list) else [parsed]:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                blocks.extend(item for item in graph if isinstance(item, dict))
            else:
                blocks.append(node)
    return blocks


def find_by_type(blocks: list[dict[str, Any]], schema_type: str) -> list[dict[str, Any]]:
    """Filter `blocks` to nodes whose `@type` is (or includes) `schema_type`."""

    matches = []
    for block in blocks:
        node_type = block.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if schema_type in types:
            matches.append(block)
    return matches
