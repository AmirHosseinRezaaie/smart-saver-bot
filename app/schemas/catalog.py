"""Internal catalog models (project document, chapter 7: Product/Price/Discount).

Plain Pydantic models, not ORM entities: persistence arrives with the
catalog sync in a later phase. They carry no trace of where the data
came from.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _CatalogModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Discount(_CatalogModel):
    amount: int = Field(gt=0)
    percent: float = Field(gt=0, le=100)


class Price(_CatalogModel):
    original_price: int = Field(ge=0)
    final_price: int = Field(ge=0)
    discount: Discount | None = None


class CatalogProduct(_CatalogModel):
    external_id: str
    name: str
    category_external_id: str | None = None
    price: Price | None = None
    in_stock: bool | None = None
    url: str | None = None
    store_name: str | None = None
