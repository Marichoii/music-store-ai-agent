# Data

Original CSVs and the policy PDF are preserved in `original/`, with SHA-256 hashes
in `manifest.json`. The catalog contains 65 products, nine categories and 25
promotions, four of them active.

Pydantic validates records and relationships. Prices use Decimal. A product is
available only when its status is `active` and stock is positive.

Search ignores case and accents. Budgets and sorting use the effective unit price
for the chosen payment method, excluding freight. `price_brl` retains the list price.

## Pricing

- Only `is_active == "1"` activates a campaign.
- Apply one active promotion; PIX gives 5% only without a promotion.
- For competing campaigns, use the largest percentage, then the lowest ID.
- Round unit prices to cents with ROUND_HALF_UP before multiplying by quantity.
- Quotes validate stock and do not create orders or reservations.

See [payment and policy assumptions](../docs/policies.md) for installment rules
and unresolved manual conditions.

## Source inconsistency

Product 144 is named Roland, but its description mentions Yamaha. Both fields are
preserved. Searches, product lookups and quotes include an explicit warning.
