"""Read and query the supplied musical instrument catalog."""

import csv
import json
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data/original"


class CatalogError(ValueError):
    """The catalog files are missing or contain invalid data."""


class CatalogRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Category(CatalogRecord):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str


class Product(CatalogRecord):
    product_id: int = Field(gt=0)
    price_brl: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    name: str = Field(min_length=1)
    category_id: int = Field(gt=0)
    description: str
    stock_quantity: int = Field(ge=0)
    status: Literal["active", "discontinued", "coming_soon"]
    specs: dict[str, str]
    created_at: date

    @field_validator("specs", mode="before")
    @classmethod
    def parse_specs(cls, value):
        return json.loads(value) if isinstance(value, str) else value

    @property
    def availability(self) -> str:
        if self.status != "active":
            return self.status
        return "available" if self.stock_quantity > 0 else "out_of_stock"


def read_records(directory: Path, table: str) -> list[dict[str, str]]:
    try:
        with (directory / f"desafio_tecnico_ai_eng - {table}.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            rows = list(csv.DictReader(source, strict=True))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CatalogError(f"Cannot read the supplied {table} CSV.") from exc
    if not rows:
        raise CatalogError(f"The {table} CSV contains no records.")
    return rows


def normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(character)
    ).strip()


class Catalog:
    def __init__(self, products: list[Product], categories: list[Category]):
        if len({p.product_id for p in products}) != len(products):
            raise CatalogError("Duplicate product IDs in the catalog.")
        if len({c.category_id for c in categories}) != len(categories):
            raise CatalogError("Duplicate category IDs in the catalog.")
        self.products = MappingProxyType({p.product_id: p for p in products})
        self.categories = MappingProxyType({c.category_id: c for c in categories})
        if any(product.category_id not in self.categories for product in products):
            raise CatalogError("A product references an unknown category.")

    @classmethod
    def load(cls, directory: Path = DEFAULT_DATA_DIR) -> "Catalog":
        try:
            return cls(
                products=[
                    Product.model_validate(row) for row in read_records(directory, "products")
                ],
                categories=[
                    Category.model_validate(row) for row in read_records(directory, "categories")
                ],
            )
        except ValidationError as exc:
            raise CatalogError("Invalid catalog values. Check the supplied CSV schema.") from exc

    def get_product(self, product_id: int) -> Product | None:
        return self.products.get(product_id)

    def search(
        self,
        query: str | None = None,
        category_id: int | None = None,
        max_price_brl: Decimal | None = None,
        available_only: bool = True,
    ) -> list[Product]:
        if category_id is not None and category_id not in self.categories:
            raise ValueError("Unknown category ID.")
        if max_price_brl is not None and (
            not isinstance(max_price_brl, Decimal)
            or not max_price_brl.is_finite()
            or max_price_brl < 0
        ):
            raise ValueError("Budget must be a finite, nonnegative Decimal amount.")
        words = normalize(query or "").split()
        matches = []
        for product in self.products.values():
            if available_only and product.availability != "available":
                continue
            if category_id is not None and product.category_id != category_id:
                continue
            if max_price_brl is not None and product.price_brl > max_price_brl:
                continue
            text = " ".join(
                [
                    product.name,
                    product.description,
                    self.categories[product.category_id].name,
                    *product.specs.values(),
                ]
            )
            if all(word in normalize(text) for word in words):
                matches.append(product)
        return sorted(matches, key=lambda product: (product.price_brl, product.product_id))
