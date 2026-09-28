"""add catalog tables (stores, categories, products, prices, discounts) and pg_trgm

Phase 4 (project document, chapter 13 / "پردازش، نرمال‌سازی و جست‌وجوی
محصول"): the first migration with real schema changes. Adds the subset of
chapter 7's data model needed to persist a synced catalog and search it —
see `app/models/catalog.py` for the corresponding ORM entities and their
per-field rationale.

Enables PostgreSQL's `pg_trgm` extension and adds a GIN trigram index on
`products.normalized_name`, per the project document's explicit choice of
`pg_trgm` over a separate search service (chapter 13, Phase 4 tool table):
fuzzy matching runs inside PostgreSQL, with no extra infrastructure.

Revision ID: 57c22fe4e768
Revises: b9a2079e6af1
Create Date: 2026-09-25 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "57c22fe4e768"
down_revision: str | Sequence[str] | None = "b9a2079e6af1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Required for `word_similarity()`/`similarity()`/the `gin_trgm_ops`
    # operator class used by the trigram index below. `IF NOT EXISTS` keeps
    # this migration safe to run against a database where an operator
    # already enabled it by hand.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("weight_default", sa.Float(), nullable=False, server_default="1.0"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("normalized_name", sa.String(length=512), nullable=False),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("store_id", "external_id", name="uq_products_store_id_external_id"),
    )
    # Exact-match stage of search (project document, chapter 13: "(۱) تطبیق
    # دقیق روی normalized_name"). A plain btree index is enough for `=`.
    op.create_index("ix_products_normalized_name", "products", ["normalized_name"])
    # Fuzzy-match stage: a GIN trigram index is what makes
    # `word_similarity()`/`%`/`similarity()` on `normalized_name` fast
    # instead of a sequential scan (project document, chapter 13, task 41).
    op.execute(
        "CREATE INDEX ix_products_normalized_name_trgm "
        "ON products USING gin (normalized_name gin_trgm_ops)"
    )

    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_price", sa.Integer(), nullable=True),
        sa.Column("final_price", sa.Integer(), nullable=True),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_prices_product_id", "prices", ["product_id"])

    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "price_id",
            sa.Integer(),
            sa.ForeignKey("prices.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("percent", sa.Float(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Drop in reverse dependency order so foreign keys never block a drop.
    op.drop_table("discounts")
    op.drop_table("prices")
    op.execute("DROP INDEX IF EXISTS ix_products_normalized_name_trgm")
    op.drop_index("ix_products_normalized_name", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("stores")
    # Left enabled by default: dropping a database-wide extension from a
    # single migration's downgrade risks breaking any other object that
    # started depending on it in the meantime. Uncomment if this is truly
    # the only consumer of pg_trgm in this database:
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm")
