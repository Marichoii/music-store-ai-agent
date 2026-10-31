"""Load and search the catalog."""

import csv
import unicodedata
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from pydantic import ValidationError

from music_store.models import Category, PaymentMethod, Product, Promotion, Quote
from music_store.payments import validate_payment_method
from music_store.pricing import price_for, quote_product

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data/original"


class CatalogError(ValueError):
    """The catalog files are missing or contain invalid data."""


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
    def __init__(
        self, products: list[Product], categories: list[Category], promotions: list[Promotion]
    ):
        if len({p.product_id for p in products}) != len(products):
            raise CatalogError("Duplicate product IDs in the catalog.")
        if len({c.category_id for c in categories}) != len(categories):
            raise CatalogError("Duplicate category IDs in the catalog.")
        if len({p.promotion_id for p in promotions}) != len(promotions):
            raise CatalogError("Duplicate promotion IDs in the catalog.")
        self.products = MappingProxyType({p.product_id: p for p in products})
        self.categories = MappingProxyType({c.category_id: c for c in categories})
        self.promotions = tuple(promotions)
        if any(product.category_id not in self.categories for product in products):
            raise CatalogError("A product references an unknown category.")
        if any(promotion.product_id not in self.products for promotion in promotions):
            raise CatalogError("A promotion references an unknown product.")

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
                promotions=[
                    Promotion.model_validate(row) for row in read_records(directory, "promotions")
                ],
            )
        except ValidationError as exc:
            raise CatalogError("Invalid catalog values. Check the supplied CSV schema.") from exc

    def get_product(self, product_id: int) -> Product | None:
        return self.products.get(product_id)

    def get_quote(
        self, product_id: int, quantity: int = 1, payment_method: PaymentMethod = "standard"
    ) -> Quote:
        product = self.get_product(product_id)
        if product is None:
            raise ValueError("Unknown product ID.")
        return quote_product(product, self.promotions, quantity, payment_method)

    def search(
        self,
        query: str | None = None,
        category_id: int | None = None,
        max_price_brl: Decimal | None = None,
        available_only: bool = True,
        payment_method: PaymentMethod = "standard",
    ) -> list[Product]:
        validate_payment_method(payment_method)
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
            unit_price = price_for(product, self.promotions, payment_method).unit_price_brl
            if max_price_brl is not None and unit_price > max_price_brl:
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
        return sorted(
            matches,
            key=lambda product: (
                price_for(product, self.promotions, payment_method).unit_price_brl,
                product.product_id,
            ),
        )
