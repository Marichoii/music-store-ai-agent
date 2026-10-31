"""Payment calculations with explicit handling of the manual's conflicting minima."""

from decimal import Decimal, InvalidOperation

from music_store.models import InstallmentPlan, PaymentMethod, PaymentTerms


def validate_payment_method(payment_method: PaymentMethod) -> None:
    if payment_method not in ("standard", "pix", "debit", "credit", "boleto"):
        raise ValueError("Unknown payment method.")


def validate_total(total: Decimal) -> None:
    if not isinstance(total, Decimal) or not total.is_finite() or total < 0:
        raise ValueError("Total must be a finite, nonnegative Decimal amount.")
    try:
        valid_precision = total == total.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError("Total cannot be represented as a BRL amount.") from exc
    if not valid_precision:
        raise ValueError("Total must have no more than two decimal places.")


def installment_options(total: Decimal) -> tuple[InstallmentPlan, ...]:
    validate_total(total)
    if total == 0:
        return ()
    total_cents = int(total * 100)
    plans = []
    for count in range(1, 13):
        base_cents, remainder = divmod(total_cents, count)
        minimum = 0 if count == 1 else (5000 if count <= 3 else (8000 if count <= 6 else 10000))
        if base_cents < minimum:
            continue
        amounts = tuple(
            (Decimal(base_cents + (index < remainder)) / 100).quantize(Decimal("0.01"))
            for index in range(count)
        )
        conflict = count > 1 and base_cents < 10000
        note = "Meets both the general and detailed installment minima."
        if count == 1:
            note = "Single credit payment; installment minima are treated as inapplicable."
        elif conflict:
            note = (
                "Allowed provisionally by section 3.1, but conflicts with section 3's "
                "BRL 100 minimum. Store confirmation is required."
            )
        plans.append(
            InstallmentPlan(
                count=count, amounts_brl=amounts, requires_confirmation=conflict, note=note
            )
        )
    return tuple(plans)


def payment_terms_for(total: Decimal, payment_method: PaymentMethod) -> PaymentTerms:
    validate_payment_method(payment_method)
    validate_total(total)
    return PaymentTerms(
        installment_options=installment_options(total) if payment_method == "credit" else (),
        mixed_payment_threshold_met=total > Decimal("2000"),
        mixed_payment_note=(
            "Threshold checked against the quoted merchandise subtotal, excluding freight. "
            "The manual permits mixed payments strictly above BRL 2000; "
            "partial-PIX discounts and checkout conditions require store confirmation. "
            "This quote does not calculate a mixed payment."
        ),
        boleto_clearance_up_to_business_days=3 if payment_method == "boleto" else None,
    )
