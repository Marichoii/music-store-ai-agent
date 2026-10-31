"""Validated source records and monetary results shared by the catalog and pricing."""

import json
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PaymentMethod = Literal["standard", "pix", "debit", "credit", "boleto"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Category(Record):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str


class Product(Record):
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


class Promotion(Record):
    promotion_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    discount_percent: Decimal = Field(gt=0, le=100, allow_inf_nan=False)
    description: str
    is_active: bool

    @field_validator("is_active", mode="before")
    @classmethod
    def parse_active(cls, value):
        if isinstance(value, bool):
            return value
        if value in ("0", "1"):
            return value == "1"
        raise ValueError("Promotion activity must be encoded as 0 or 1.")


class PriceBreakdown(Record):
    list_price_brl: Decimal
    unit_price_brl: Decimal
    discount_percent: Decimal
    discount_source: Literal["none", "promotion", "pix"]
    promotion: Promotion | None


class Quote(Record):
    product_id: int
    name: str
    quantity: int
    payment_method: PaymentMethod
    price: PriceBreakdown
    subtotal_brl: Decimal
    currency: Literal["BRL"] = "BRL"
    freight_included: bool = False
