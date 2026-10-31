from decimal import Decimal

import pytest

from music_store.catalog import Catalog
from music_store.payments import installment_options, payment_terms_for


@pytest.mark.parametrize(
    "total,maximum",
    [
        ("49.99", 1),
        ("99.99", 1),
        ("100.00", 2),
        ("150.00", 3),
        ("319.99", 3),
        ("320.00", 4),
        ("479.99", 5),
        ("480.00", 6),
        ("699.99", 6),
        ("700.00", 7),
        ("1200.00", 12),
    ],
)
def test_installment_boundaries(total, maximum):
    plans = installment_options(Decimal(total))
    assert max(plan.count for plan in plans) == maximum


def test_remainder_cents_sum_to_total_without_violating_tier_minima():
    total = Decimal("599.90")
    plans = installment_options(total)
    for plan in plans:
        assert len(plan.amounts_brl) == plan.count
        assert sum(plan.amounts_brl) == total
        assert plan.interest_percent == 0
        minimum = (
            Decimal("0")
            if plan.count == 1
            else Decimal("50" if plan.count <= 3 else "80" if plan.count <= 6 else "100")
        )
        assert min(plan.amounts_brl) >= minimum
        assert max(plan.amounts_brl) - min(plan.amounts_brl) <= Decimal("0.01")
    six = next(plan for plan in plans if plan.count == 6)
    assert six.amounts_brl == (
        Decimal("99.99"),
        Decimal("99.99"),
        Decimal("99.98"),
        Decimal("99.98"),
        Decimal("99.98"),
        Decimal("99.98"),
    )


def test_conflicting_plans_require_confirmation():
    plans = installment_options(Decimal("599.90"))
    assert next(plan for plan in plans if plan.count == 6).requires_confirmation
    assert "section 3" in next(plan for plan in plans if plan.count == 6).note
    assert not next(plan for plan in plans if plan.count == 3).requires_confirmation
    small = installment_options(Decimal("100"))
    assert next(plan for plan in small if plan.count == 2).requires_confirmation


def test_zero_quote_needs_no_payment_schedule():
    assert installment_options(Decimal("0.00")) == ()


@pytest.mark.parametrize(
    "total",
    [
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("100.001"),
        100.0,
    ],
)
def test_invalid_total_cannot_generate_a_schedule(total):
    with pytest.raises(ValueError):
        installment_options(total)


@pytest.mark.parametrize("method", ["standard", "pix", "debit", "boleto"])
def test_installment_options_are_only_attached_to_credit(method):
    terms = payment_terms_for(Decimal("1200"), method)
    assert terms.installment_options == ()


@pytest.mark.parametrize(
    "amount,threshold_met",
    [
        ("1999.99", False),
        ("2000.00", False),
        ("2000.01", True),
    ],
)
def test_mixed_payment_threshold_is_strict_and_qualified(amount, threshold_met):
    terms = payment_terms_for(Decimal(amount), "standard")
    assert terms.mixed_payment_threshold_met == threshold_met
    assert "excluding freight" in terms.mixed_payment_note
    assert "require store confirmation" in terms.mixed_payment_note
    assert "does not calculate a mixed payment" in terms.mixed_payment_note


def test_boleto_compensation_is_an_upper_bound_not_an_arrival_date():
    terms = payment_terms_for(Decimal("599.90"), "boleto")
    assert terms.boleto_clearance_up_to_business_days == 3
    assert payment_terms_for(Decimal("599.90"), "pix").boleto_clearance_up_to_business_days is None
    assert "p. 3" in terms.source


def test_quote_includes_json_serializable_payment_terms():
    catalog = Catalog.load()
    quote = catalog.get_quote(81, payment_method="credit")
    assert quote.subtotal_brl == Decimal("599.90")
    data = quote.model_dump(mode="json")
    plans = data["payment_terms"]["installment_options"]
    assert next(plan for plan in plans if plan["count"] == 6)["requires_confirmation"]
    assert next(plan for plan in plans if plan["count"] == 1)["amounts_brl"] == ["599.90"]


def test_unknown_payment_method_is_rejected():
    with pytest.raises(ValueError, match="payment method"):
        payment_terms_for(Decimal("100"), "cash")
