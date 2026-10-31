# Catalog and pricing data

`original/` contains the unmodified products, categories and promotions CSVs and
the policy PDF from the supplied challenge ZIP. Archive paths and SHA-256 hashes are recorded in
`original/manifest.json`. Git line-ending conversion is disabled for these files.
The remaining materials are preserved in the original ZIP and will be introduced
as their features are implemented.

The catalog loads 65 products, nine categories and 25 promotions. IDs and
relationships are validated with Pydantic, prices use Decimal, specifications are parsed from JSON,
and creation dates are parsed as dates. Missing files or invalid records produce
a CatalogError instead of a partial catalog.

Availability requires both `status == "active"` and positive stock. The supplied
data includes an out-of-stock active product, discontinued products, and an
upcoming product with recorded stock. Positive stock does not override status.
Known categories with no product rows return an empty search result.

Search combines name/description/specification keywords, category and budget.
Matching ignores case and accents. Budgets and sorting use the effective unit
price for the selected payment method, excluding freight. A product's `price_brl`
always retains the original list price; use `get_quote` for a calculated price.

## Pricing rules

Four promotions are active: #12 (product 127, 10%), #14 (121, 20%), #19 (90, 18%)
and #24 (94, 8%). Only `is_active == "1"` activates a campaign. The name of a
campaign and the current month do not establish its validity.

The manual's sections 3 and 6.2 (pages 3 and 6) give a 5% PIX discount on list
prices and prohibit stacking PIX with promotional prices. One active campaign is
applied instead of the PIX discount. If multiple active campaigns match, the
implementation uses the greatest percentage once, breaking ties by the lowest
promotion ID. This tie rule is an explicit assumption; the supplied data does not
contain competing active campaigns for the same product.

Prices use Decimal and ROUND_HALF_UP. Round the discounted unit price to cents
before multiplying by quantity. Quotes contain the original price, final unit
price, percentage, discount source, promotion details and subtotal. Unavailable
products and quantities beyond stock cannot be quoted.

Quotes do not reserve stock, place orders or include freight. Credit quotes now
include installment schedules with confirmation flags for conflicting minima;
mixed-payment threshold and boleto conditions are also included. Full manual
context and the assumptions behind those rules are documented in
[policies.md](../docs/policies.md).

## Source inconsistency

Product 144 is named Roland, but its description mentions Yamaha. Both fields are
preserved as supplied. Description matches do not establish a product's brand;
use the product ID and name for identification and flag conflicting details.

## Example

```python
from decimal import Decimal
from music_store.catalog import Catalog

catalog = Catalog.load()
products = catalog.search(category_id=5, max_price_brl=Decimal("1000"), payment_method="pix")
for product in products:
    quote = catalog.get_quote(product.product_id, payment_method="pix")
    print(quote.name, quote.price.unit_price_brl, quote.price.discount_source)
```

Run the catalog tests with `uv run pytest -q`.
