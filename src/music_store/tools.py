"""Validated, read-only tools for the agent."""

import json
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from music_store.catalog import Catalog, normalize
from music_store.models import PaymentMethod, Product
from music_store.policies import PolicyBook
from music_store.pricing import price_for

PRODUCT_DATA_NOTES = {
    144: (
        "The product name identifies Roland, but its description identifies Yamaha. "
        "The source does not resolve the conflict; confirm the brand/model with the store."
    ),
}


def data_quality_notes(product: Product) -> list[str]:
    note = PRODUCT_DATA_NOTES.get(product.product_id)
    return [note] if note else []


class ToolInputError(ValueError):
    pass


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchArguments(Arguments):
    query: str | None = Field(default=None, max_length=200)
    category_id: int | None = Field(default=None, gt=0)
    max_price_brl: str | None = Field(
        default=None, description="Decimal BRL string, e.g. '1000.00'."
    )
    available_only: bool = True
    payment_method: PaymentMethod = "standard"
    limit: int = Field(default=10, ge=1, le=20)


class ProductArguments(Arguments):
    query: str = Field(
        min_length=1, max_length=200, description="Exact ID or product-name fragment."
    )


class QuoteArguments(Arguments):
    product_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=100)
    payment_method: PaymentMethod = "standard"


TOOL_TYPES = {
    "list_categories": (
        Arguments,
        "List category IDs and product counts, including empty categories.",
    ),
    "search_catalog": (
        SearchArguments,
        "Search by source-language keywords, category, availability and effective budget. "
        "Returns compact results; use get_product for descriptions and specifications.",
    ),
    "get_product": (
        ProductArguments,
        "Find a product by ID or name. Multiple candidates require clarification.",
    ),
    "quote_product": (
        QuoteArguments,
        "Calculate prices, discounts, quantities and payment terms. Creates no order.",
    ),
    "get_store_policies": (
        Arguments,
        "Read the complete policy manual with page references and ambiguity notes.",
    ),
}


def tool_definitions() -> list[dict]:
    return [
        {
            "name": name,
            "description": description,
            "parameters_json_schema": model.model_json_schema(),
        }
        for name, (model, description) in TOOL_TYPES.items()
    ]


def parse_budget(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ToolInputError("Use a decimal budget such as '1000.00'.") from exc
    if not amount.is_finite() or amount < 0 or amount > Decimal("10000000"):
        raise ToolInputError("Budget must be between 0 and 10000000 BRL.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ToolInputError("Budget must have no more than two decimal places.")
    return amount


class StoreTools:
    def __init__(self, catalog: Catalog, policies: PolicyBook):
        self.catalog = catalog
        self.policies = policies

    def describe(
        self, product: Product, method: PaymentMethod = "standard", *, summary: bool = False
    ) -> dict:
        excluded = {"description", "specs", "created_at", "price_brl"} if summary else None
        return {
            **product.model_dump(mode="json", exclude=excluded),
            "category": self.catalog.categories[product.category_id].name,
            "availability": product.availability,
            "price": price_for(product, self.catalog.promotions, method).model_dump(mode="json"),
            "data_quality_notes": data_quality_notes(product),
            "source": f"products.csv, product_id={product.product_id}; promotions.csv",
        }

    def list_categories(self, args: Arguments) -> dict:
        return {
            "categories": [
                {
                    **category.model_dump(),
                    "product_count": sum(
                        product.category_id == category.category_id
                        for product in self.catalog.products.values()
                    ),
                }
                for category in self.catalog.categories.values()
            ],
            "source": "categories.csv",
        }

    def search_catalog(self, args: SearchArguments) -> dict:
        if args.category_id is not None and args.category_id not in self.catalog.categories:
            raise ToolInputError("Unknown category ID. Use list_categories first.")
        products = self.catalog.search(
            query=args.query,
            category_id=args.category_id,
            max_price_brl=parse_budget(args.max_price_brl),
            available_only=args.available_only,
            payment_method=args.payment_method,
        )
        return {
            "products": [
                self.describe(product, args.payment_method, summary=True)
                for product in products[: args.limit]
            ],
            "total_matches": len(products),
            "truncated": len(products) > args.limit,
            "budget_basis": "Effective unit price for the selected payment, excluding freight.",
        }

    def get_product(self, args: ProductArguments) -> dict:
        query = normalize(args.query)
        if not query:
            raise ToolInputError("A product ID or name is required.")
        if query.isdigit():
            product = self.catalog.get_product(int(query))
            matches = [product] if product else []
        else:
            exact = [p for p in self.catalog.products.values() if normalize(p.name) == query]
            matches = exact or [
                p
                for p in self.catalog.products.values()
                if all(word in normalize(p.name) for word in query.split())
            ]
        if not matches:
            return {"status": "not_found", "query": args.query}
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "requires_clarification": True,
                "candidates": [self.describe(p) for p in matches[:10]],
                "total_matches": len(matches),
            }
        product = matches[0]
        alternatives = []
        if product.availability != "available":
            available = self.catalog.search(category_id=product.category_id)
            available.sort(key=lambda p: (abs(p.price_brl - product.price_brl), p.product_id))
            alternatives = [self.describe(p) for p in available[:3]]
        return {
            "status": "found",
            "product": self.describe(product),
            "promotions": [
                p.model_dump(mode="json")
                for p in self.catalog.promotions
                if p.product_id == product.product_id
            ],
            "alternatives": alternatives,
            "alternative_basis": "Same category and nearby list prices; no confirmed successor.",
        }

    def quote_product(self, args: QuoteArguments) -> dict:
        product = self.catalog.get_product(args.product_id)
        if product is None:
            return {"status": "not_found", "product_id": args.product_id}
        if product.availability != "available":
            return {"status": "unavailable", "product": self.describe(product)}
        if args.quantity > product.stock_quantity:
            return {"status": "insufficient_stock", "stock_quantity": product.stock_quantity}
        quote = self.catalog.get_quote(args.product_id, args.quantity, args.payment_method)
        return {
            "status": "quoted",
            **quote.model_dump(mode="json"),
            "data_quality_notes": data_quality_notes(product),
            "source": "products.csv; promotions.csv; manual sections 3 and 6.2, pp. 3, 6",
            "action": "Read-only quote; no order or reservation created.",
        }

    def get_store_policies(self, args: Arguments) -> dict:
        return self.policies.context()

    def execute(self, name: str, arguments: str) -> dict:
        if name not in TOOL_TYPES:
            return {"ok": False, "error": "unknown_tool", "message": "This tool is unavailable."}
        try:
            if len(arguments) > 8000:
                raise ToolInputError("Tool arguments are too long.")
            values = json.loads(arguments)
            if isinstance(values, dict):
                for field in ("product_id", "quantity", "category_id", "limit"):
                    value = values.get(field)
                    if type(value) is float and value.is_integer():
                        values[field] = int(value)
            args = TOOL_TYPES[name][0].model_validate(values)
            return {"ok": True, "data": getattr(self, name)(args)}
        except ToolInputError as exc:
            return {"ok": False, "error": "invalid_arguments", "message": str(exc)}
        except (ValidationError, json.JSONDecodeError):
            return {
                "ok": False,
                "error": "invalid_arguments",
                "message": "Use the declared schema.",
            }
        except Exception:
            return {
                "ok": False,
                "error": "source_unavailable",
                "message": "The source could not be verified. Do not invent a result.",
            }
