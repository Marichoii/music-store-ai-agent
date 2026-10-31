# Catalog data

`original/` contains the unmodified products and categories CSVs from the supplied
challenge ZIP. Their archive paths and SHA-256 hashes are recorded in
`original/manifest.json`. Git line-ending conversion is disabled for these files.
The remaining materials are preserved in the original ZIP and will be introduced
as their features are implemented.

The catalog loads 65 products and nine categories. IDs and relationships are
validated with Pydantic, prices use Decimal, specifications are parsed from JSON,
and creation dates are parsed as dates. Missing files or invalid records produce
a CatalogError instead of a partial catalog.

Availability requires both `status == "active"` and positive stock. The supplied
data includes an out-of-stock active product, discontinued products, and an
upcoming product with recorded stock. Positive stock does not override status.
Known categories with no product rows return an empty search result.

Search combines name/description/specification keywords, category and budget.
Matching ignores case and accents. Results are ordered by price and product ID.
At this stage, budgets use **list prices**; promotions and payment discounts will
be implemented in a separate step.

Product 144 is named Roland, but its description mentions Yamaha. Both fields are
preserved as supplied. Description matches do not establish a product's brand;
use the product ID and name for identification and flag conflicting details.

```python
from decimal import Decimal
from music_store.catalog import Catalog

catalog = Catalog.load()
products = catalog.search(category_id=5, max_price_brl=Decimal("1000"))
for product in products:
    print(product.product_id, product.name, product.price_brl, product.availability)
```

Run the catalog tests with `uv run pytest -q`.
