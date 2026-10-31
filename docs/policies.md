# Policy manual and payment assumptions

The original eight-page `políticas_da_loja.pdf` is preserved under `data/original/`
and included in its SHA-256 manifest. The manual is version 2.1, June 2025. It is
a supplied source snapshot, not evidence of current law, carrier tracking or
updated store conditions.

`PolicyBook.context()` returns every page with its physical PDF page number,
alongside explicit interpretation notes. The manual is short enough to provide
in full when the agent needs policies. No embeddings, vector database or top-k
retrieval are needed; keeping all pages avoids dropping conflicting sections or
paragraphs that continue on the next page. A missing, unreadable, encrypted or
textless PDF produces a PolicyError. OCR is not implemented.

## Source conflicts and gaps

- **Identity and location:** the current project README uses Music Store in
  Brasília. The original manual describes Empório da Música in Campo Grande/MS.
  The PDF is not rewritten. Customer-facing answers must identify this source
  conflict and clarify the intended location before applying regional conditions.
- **Contacts (pp. 1–2, 6):** the cover/company table give `(67) 3341-4444`, while
  section 7 gives WhatsApp `(67) 3321-4500`. Email spellings also differ. Neither
  is treated as verified contact information by the application.
- **Installments (p. 3):** section 3 says a BRL 100 minimum; section 3.1 permits
  lower tiered minima. Detailed tiers are used provisionally. Any plan conflicting
  with the general minimum has `requires_confirmation=True`.
- **Shipping (pp. 4–5):** local freight is specified strictly above/below BRL 500,
  leaving exactly BRL 500 undefined. Its before/after-discount basis is missing.
  Other-city prices require unavailable destination/weight/dimension quotations;
  large instruments can require individual quotes. No carrier, postal coverage
  or exact arrival-date service is connected. Published windows are estimates.
- **Returns (p. 4):** online regret has a seven-calendar-day period from receipt.
  The preference-exchange period has no explicit starting event. Customized and
  final-sale exclusions can overlap with regret/defect/warranty sections. Explain
  the source, ask for missing facts, and request human review for ambiguous cases
  instead of denying a return or warranty request categorically. A clearance
  campaign is not evidence of an explicit final-sale notice.
- **Warranty (pp. 4, 7):** distinguish the manual's 30-day store defect-exchange
  window counted from purchase and its 90-day warranty counted from receipt. Manufacturer-specific
  certificates are absent. The prototype does not give an independent legal opinion.
- **Capabilities (pp. 6–8):** the manual describes complaint registration,
  human follow-up and deletion requests. The prototype can explain them, but has
  no backend that performs those actions. It also has no authenticated order
  lookup, checkout, refund or reservation capability.
- **Opening times:** the published schedule is available on p. 2, but no holiday
  or special-opening calendar is connected. Do not invent exceptions or an exact
  reopening date.

## Payment calculations

`payments.py` applies the detailed installment tiers to the quoted merchandise
subtotal: BRL 50 per payment for 2–3 installments, BRL 80 for 4–6, and BRL 100 for
7–12. The awkward below-BRL-50 exception is interpreted as a per-installment floor.
A single credit payment is treated as non-installment and has no such floor.
These are documented interpretations, not store-confirmed resolutions of the
manual's conflicting wording.

Amounts are split in integer cents. Remainder cents go to the first payments, so
every plan sums exactly to the subtotal. A zero-price quote has no payment schedule.
Installment options appear only for credit quotes; any option below the general
BRL 100 minimum explicitly requires store confirmation.

The manual permits mixed payment methods strictly above BRL 2,000. The quote
reports whether its merchandise subtotal crosses that threshold, excluding
freight; it does not approve checkout or calculate partial-PIX discounts. Those
conditions require confirmation. Boleto clearance is shown as **up to three
business days**, without inventing an actual clearance or delivery date.

## Example

```python
from music_store.catalog import Catalog
from music_store.policies import PolicyBook

context = PolicyBook().context()
quote = Catalog.load().get_quote(81, payment_method="credit")
for plan in quote.payment_terms.installment_options:
    print(plan.count, plan.amounts_brl, plan.requires_confirmation)
```

This is backend verification code, not an executed LLM conversation. The agent
and chat interface will consume these sources in later steps.
