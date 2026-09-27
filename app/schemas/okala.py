"""Raw, provider-neutral schemas returned by `OkalaProviderInterface`.

These describe what the Data Provider layer hands to the rest of the
application. They are deliberately *not* the wire format of any specific
external source: each concrete adapter validates its own wire payload
and maps it onto these models, so a change of data source never leaks
past `app/scrapers`.

Every field that OKALA might not expose (see docs/okala-research.md) is
nullable; downstream logic must not depend on it being present.
"""

from __future__ import annotations

from typing import Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class _RawModel(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")


class Category(_RawModel):
    """A product category as reported by the provider."""

    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parent_external_id: str | None = None


class RawProduct(_RawModel):
    """A product as it appears in a category listing. Prices are whole Toman."""

    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category_external_id: str | None = None
    original_price: int | None = Field(default=None, ge=0)
    final_price: int | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def _final_price_not_above_original(self) -> Self:
        if (
            self.original_price is not None
            and self.final_price is not None
            and self.final_price > self.original_price
        ):
            raise ValueError("final_price must not exceed original_price")
        return self


class RawProductDetail(RawProduct):
    """A single product's detail view; additionally identifies the store."""

    store_name: str = Field(min_length=1)
