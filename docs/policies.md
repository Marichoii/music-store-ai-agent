# Store policies

The original manual, v2.1 (June 2025), is preserved in `data/original/`.
`PolicyBook.context()` returns all eight pages with page references and notes.
Missing, encrypted or unreadable files raise `PolicyError`. OCR is not implemented.

## Interpretations

- **Location:** Empório da Música, Campo Grande/MS. Local delivery covers the
  metropolitan region described in the manual.
- **Contacts (pp. 1–2, 6):** phone numbers and email spellings conflict. Report the
  discrepancy instead of presenting either contact as verified.
- **Installments (p. 3):** the general BRL 100 minimum conflicts with detailed
  tiers. Plans relying on lower minima require store confirmation.
- **Freight (pp. 4–5):** exactly BRL 500 and the pre/post-discount threshold basis
  are undefined. Other-city and large-item fees require a quote. Delivery windows
  are estimates; no carrier or coverage service is connected.
- **Returns (p. 4):** online regret starts at receipt; preference exchanges have
  no explicit starting event. Overlapping exclusions require human review.
- **Warranty (pp. 4, 7):** store defect exchange is 30 days from purchase; the
  manual's warranty is 90 days from receipt. Manufacturer terms need a certificate.
- **Actions:** the assistant provides information, without registering complaints,
  processing refunds, reserving stock or deleting personal data.

## Payments

Provisional installment floors: BRL 50 for 2–3x, BRL 80 for 4–6x and BRL 100 for
7–12x. Single payments have no floor. Remainder cents go to the first payments;
amounts always sum to the subtotal. A zero-price quote has no payment schedule.

Mixed-payment eligibility is checked strictly above BRL 2,000 using the merchandise
subtotal, excluding freight. Partial-PIX terms require confirmation and are not
calculated. Boleto clearance is up to three business days.
