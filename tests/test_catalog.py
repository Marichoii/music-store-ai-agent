import csv
import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from music_store.catalog import DEFAULT_DATA_DIR, Catalog, CatalogError


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


@pytest.fixture
def source_copy(tmp_path):
    for table in ("products", "categories"):
        filename = f"desafio_tecnico_ai_eng - {table}.csv"
        shutil.copyfile(DEFAULT_DATA_DIR / filename, tmp_path / filename)
    return tmp_path


def change_first_record(directory: Path, table: str, field: str, value: str):
    filename = directory / f"desafio_tecnico_ai_eng - {table}.csv"
    with filename.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames
        rows = list(reader)
    rows[0][field] = value
    with filename.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_original_files_match_source_manifest():
    manifest = json.loads((DEFAULT_DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 2
    for entry in manifest["files"]:
        raw = (DEFAULT_DATA_DIR / entry["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        assert len(raw) == entry["size_bytes"]


def test_loads_complete_catalog_and_parses_types(catalog):
    assert len(catalog.products) == 65
    assert len(catalog.categories) == 9
    product = catalog.get_product(81)
    assert product.price_brl == Decimal("599.90")
    assert isinstance(product.price_brl, Decimal)
    assert product.specs["strings"] == "nylon"
    assert product.created_at.isoformat() == "2021-03-15"


def test_available_guitars_within_budget(catalog):
    products = catalog.search(category_id=5, max_price_brl=Decimal("1000"))
    assert products
    assert all(product.category_id == 5 for product in products)
    assert all(product.price_brl <= Decimal("1000") for product in products)
    assert all(product.availability == "available" for product in products)
    assert products == sorted(products, key=lambda product: (product.price_brl, product.product_id))


@pytest.mark.parametrize(
    "product_id,availability",
    [
        (96, "out_of_stock"),
        (113, "discontinued"),
        (130, "coming_soon"),
        (136, "discontinued"),
    ],
)
def test_unavailable_statuses_are_distinct_and_excluded(catalog, product_id, availability):
    product = catalog.get_product(product_id)
    assert product.availability == availability
    assert product not in catalog.search()
    assert product in catalog.search(available_only=False)


def test_positive_stock_does_not_override_discontinued_or_upcoming(catalog):
    assert catalog.get_product(136).stock_quantity == 13
    assert catalog.get_product(130).stock_quantity == 2
    assert len(catalog.search()) == 61


def test_unknown_product_is_different_from_unavailable_product(catalog):
    assert catalog.get_product(99999) is None
    assert catalog.get_product(96) is not None
    assert catalog.search(query="Imaginary instrument 9000") == []


def test_case_accents_and_combined_filters(catalog):
    assert [p.product_id for p in catalog.search(query="YAMAHA c40")] == [81]
    assert [p.product_id for p in catalog.search(query="Takamine GD20")] == [95]
    products = catalog.search(query="aco", category_id=5, max_price_brl=Decimal("1000"))
    assert products
    assert all(product.specs["strings"] == "steel" for product in products)
    assert catalog.search(query="nylon", category_id=5, max_price_brl=Decimal("400")) == []


def test_ambiguous_name_keeps_all_candidates(catalog):
    products = catalog.search(query="Yamaha")
    assert len(products) > 1
    assert {81, 82, 87}.issubset({product.product_id for product in products})


def test_empty_category_and_unknown_category_are_different(catalog):
    assert 6 in catalog.categories
    assert catalog.search(category_id=6) == []
    with pytest.raises(ValueError, match="Unknown category"):
        catalog.search(category_id=999)


def test_budget_is_inclusive_and_uses_list_price(catalog):
    product = catalog.get_product(81)
    assert product in catalog.search(max_price_brl=Decimal("599.90"))
    assert product not in catalog.search(max_price_brl=Decimal("599.89"))
    assert catalog.get_product(121) not in catalog.search(max_price_brl=Decimal("500"))


@pytest.mark.parametrize("budget", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), 1000.0])
def test_invalid_budgets_are_rejected(catalog, budget):
    with pytest.raises(ValueError, match="Budget"):
        catalog.search(max_price_brl=budget)


@pytest.mark.parametrize(
    "field,value",
    [
        ("price_brl", "NaN"),
        ("price_brl", "-10"),
        ("stock_quantity", "-1"),
        ("status", "unexpected_status"),
        ("specs", "not JSON"),
        ("created_at", "not a date"),
    ],
)
def test_invalid_source_values_fail_instead_of_loading_partial_data(source_copy, field, value):
    change_first_record(source_copy, "products", field, value)
    with pytest.raises(CatalogError, match="Invalid catalog values"):
        Catalog.load(source_copy)


@pytest.mark.parametrize(
    "table,field,value,message",
    [
        ("products", "product_id", "82", "Duplicate product"),
        ("categories", "category_id", "2", "Duplicate category"),
        ("products", "category_id", "999", "unknown category"),
    ],
)
def test_invalid_ids_and_relationships_are_rejected(source_copy, table, field, value, message):
    change_first_record(source_copy, table, field, value)
    with pytest.raises(CatalogError, match=message):
        Catalog.load(source_copy)


def test_missing_source_is_actionable(tmp_path):
    with pytest.raises(CatalogError, match="Cannot read"):
        Catalog.load(tmp_path)


def test_empty_source_is_rejected(source_copy):
    filename = source_copy / "desafio_tecnico_ai_eng - products.csv"
    filename.write_text("product_id,price_brl\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="no records"):
        Catalog.load(source_copy)
