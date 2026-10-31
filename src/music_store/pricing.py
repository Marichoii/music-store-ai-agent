"""Calculate prices and quotes."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from music_store.models import PaymentMethod, PriceBreakdown, Product, Promotion, Quote
from music_store.payments import payment_terms_for, validate_payment_method


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_for(
    product: Product,
    promotions: Iterable[Promotion],
    payment_method: PaymentMethod = "standard",
) -> PriceBreakdown:
    validate_payment_method(payment_method)
    promotion = max(
        (
            offer
            for offer in promotions
            if offer.product_id == product.product_id
            and offer.is_active
            and product.availability == "available"
        ),
        key=lambda offer: (offer.discount_percent, -offer.promotion_id),
        default=None,
    )
    discount = Decimal("0")
    discount_source = "none"
    if promotion is not None:
        discount = promotion.discount_percent
        discount_source = "promotion"
    elif payment_method == "pix" and product.availability == "available":
        discount = Decimal("5")
        discount_source = "pix"
    list_price = money(product.price_brl)
    return PriceBreakdown(
        list_price_brl=list_price,
        unit_price_brl=money(list_price * (Decimal("1") - discount / Decimal("100"))),
        discount_percent=discount,
        discount_source=discount_source,
        promotion=promotion,
    )


def quote_product(
    product: Product,
    promotions: Iterable[Promotion],
    quantity: int = 1,
    payment_method: PaymentMethod = "standard",
) -> Quote:
    if product.availability != "available":
        raise ValueError(f"Product is {product.availability}; a quote is not available.")
    if type(quantity) is not int or quantity < 1:
        raise ValueError("Quantity must be a positive integer.")
    if quantity > product.stock_quantity:
        raise ValueError("Requested quantity exceeds the available stock.")
    price = price_for(product, promotions, payment_method)
    subtotal = money(price.unit_price_brl * quantity)
    return Quote(
        product_id=product.product_id,
        name=product.name,
        quantity=quantity,
        payment_method=payment_method,
        price=price,
        subtotal_brl=subtotal,
        payment_terms=payment_terms_for(subtotal, payment_method),
    )
