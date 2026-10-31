import csv
import shutil
from decimal import Decimal

import pytest
from pydantic import ValidationError

from music_store.catalog import DEFAULT_DATA_DIR, Catalog, CatalogError
from music_store.models import Promotion
from music_store.pricing import money, price_for, quote_product


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


def test_promotion_activity_comes_from_the_flag(catalog):
    assert len(catalog.promotions) == 25
    assert {p.promotion_id for p in catalog.promotions if p.is_active} == {12, 14, 19, 24}
    assert not next(p for p in catalog.promotions if p.promotion_id == 4).is_active


@pytest.mark.parametrize(
    "product_id,original,final,percent",
    [
        (127, "359.00", "323.10", "10"),
        (121, "549.00", "439.20", "20"),
        (90, "2399.00", "1967.18", "18"),
        (94, "5999.00", "5519.08", "8"),
    ],
)
def test_all_active_campaigns_and_pix_do_not_stack(catalog, product_id, original, final, percent):
    quote = catalog.get_quote(product_id, payment_method="pix")
    assert quote.price.list_price_brl == Decimal(original)
    assert quote.price.unit_price_brl == Decimal(final)
    assert quote.price.discount_percent == Decimal(percent)
    assert quote.price.discount_source == "promotion"
    assert quote.price.promotion.is_active


def test_inactive_campaign_does_not_change_current_price(catalog):
    standard = catalog.get_quote(95)
    pix = catalog.get_quote(95, payment_method="pix")
    assert standard.price.unit_price_brl == Decimal("2199.00")
    assert standard.price.discount_source == "none"
    assert standard.price.promotion is None
    assert pix.price.unit_price_brl == Decimal("2089.05")
    assert pix.price.discount_source == "pix"


def test_money_rounds_half_up_before_multiplying_quantity(catalog):
    quote = catalog.get_quote(81, quantity=2, payment_method="pix")
    assert quote.price.unit_price_brl == Decimal("569.91")
    assert quote.subtotal_brl == Decimal("1139.82")
    assert money(Decimal("1.005")) == Decimal("1.01")
    assert not quote.freight_included and quote.currency == "BRL"


def test_quote_is_json_serializable_without_float_prices(catalog):
    data = catalog.get_quote(121, payment_method="pix").model_dump(mode="json")
    assert data["price"]["list_price_brl"] == "549.00"
    assert data["price"]["unit_price_brl"] == "439.20"
    assert data["subtotal_brl"] == "439.20"
    assert data["price"]["promotion"]["is_active"] is True


def test_effective_budget_uses_the_selected_payment_method(catalog):
    product = catalog.get_product(81)
    assert product not in catalog.search(max_price_brl=Decimal("570"))
    assert product in catalog.search(max_price_brl=Decimal("570"), payment_method="pix")
    products = catalog.search(category_id=9, max_price_brl=Decimal("440"))
    assert catalog.get_product(121) in products
    prices = [catalog.get_quote(p.product_id).price.unit_price_brl for p in products]
    assert prices == sorted(prices)
    assert all(price <= Decimal("440") for price in prices)


def test_best_campaign_is_applied_once_with_deterministic_ties(catalog):
    product = catalog.get_product(81)
    campaigns = [
        Promotion(
            promotion_id=902,
            product_id=81,
            discount_percent="20",
            description="One campaign",
            is_active=True,
        ),
        Promotion(
            promotion_id=901,
            product_id=81,
            discount_percent="20",
            description="Another campaign",
            is_active=True,
        ),
        Promotion(
            promotion_id=900,
            product_id=81,
            discount_percent="10",
            description="Lower discount",
            is_active=True,
        ),
    ]
    price = price_for(product, campaigns, "pix")
    assert price.unit_price_brl == Decimal("479.92")
    assert price.promotion.promotion_id == 901
    assert price.discount_percent == Decimal("20")


def test_campaign_name_does_not_activate_a_discount(catalog):
    promotion = Promotion(
        promotion_id=900,
        product_id=81,
        discount_percent="80",
        description="Black Friday",
        is_active=False,
    )
    price = price_for(catalog.get_product(81), [promotion])
    assert price.unit_price_brl == Decimal("599.90") and price.promotion is None


@pytest.mark.parametrize("product_id", [96, 113, 130, 136])
def test_unavailable_products_cannot_be_quoted(catalog, product_id):
    with pytest.raises(ValueError, match="quote is not available"):
        catalog.get_quote(product_id, payment_method="pix")
    price = price_for(catalog.get_product(product_id), catalog.promotions, "pix")
    assert price.discount_percent == 0 and price.promotion is None


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5, "1"])
def test_invalid_quantities_are_rejected(catalog, quantity):
    with pytest.raises(ValueError, match="positive integer"):
        catalog.get_quote(81, quantity=quantity)


def test_unknown_product_and_excess_quantity_are_distinct(catalog):
    with pytest.raises(ValueError, match="Unknown product"):
        catalog.get_quote(99999)
    with pytest.raises(ValueError, match="exceeds"):
        catalog.get_quote(81, quantity=13)


def test_quote_does_not_reserve_or_decrement_stock(catalog):
    original_stock = catalog.get_product(81).stock_quantity
    catalog.get_quote(81, quantity=original_stock)
    assert catalog.get_product(81).stock_quantity == original_stock


@pytest.mark.parametrize("method", ["debit", "credit", "boleto"])
def test_other_payment_methods_do_not_receive_the_pix_discount(catalog, method):
    assert catalog.get_quote(81, payment_method=method).price.unit_price_brl == Decimal("599.90")


def test_unknown_payment_method_is_rejected_even_for_empty_results(catalog):
    with pytest.raises(ValueError, match="payment method"):
        catalog.get_quote(81, payment_method="cash")
    with pytest.raises(ValueError, match="payment method"):
        catalog.search(category_id=6, payment_method="cash")


@pytest.mark.parametrize("value", ["true", "false", "yes", "", "2"])
def test_activity_does_not_coerce_arbitrary_strings(value):
    with pytest.raises(ValidationError):
        Promotion(
            promotion_id=900,
            product_id=81,
            discount_percent="10",
            description="Invalid activity",
            is_active=value,
        )


@pytest.mark.parametrize("discount", ["-1", "0", "101", "NaN", "Infinity"])
def test_invalid_promotion_percentages_are_rejected(discount):
    with pytest.raises(ValidationError):
        Promotion(
            promotion_id=900,
            product_id=81,
            discount_percent=discount,
            description="Invalid percentage",
            is_active=True,
        )


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("promotion_id", "2", "Duplicate promotion"),
        ("product_id", "99999", "unknown product"),
        ("is_active", "true", "Invalid catalog values"),
    ],
)
def test_invalid_promotion_source_fails_closed(tmp_path, field, value, message):
    for table in ("products", "categories", "promotions"):
        filename = f"desafio_tecnico_ai_eng - {table}.csv"
        shutil.copyfile(DEFAULT_DATA_DIR / filename, tmp_path / filename)
    path = tmp_path / "desafio_tecnico_ai_eng - promotions.csv"
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames
        rows = list(reader)
    rows[0][field] = value
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(CatalogError, match=message):
        Catalog.load(tmp_path)


def test_full_discount_remains_a_zero_price_instead_of_missing_data(catalog):
    promotion = Promotion(
        promotion_id=900,
        product_id=81,
        discount_percent="100",
        description="Full discount",
        is_active=True,
    )
    quote = quote_product(catalog.get_product(81), [promotion], payment_method="pix")
    assert quote.price.unit_price_brl == Decimal("0.00")
    assert quote.subtotal_brl == Decimal("0.00")
