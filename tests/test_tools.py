import json

import pytest

from music_store.tools import TOOL_TYPES, tool_definitions


def call(tools, name, **arguments):
    return tools.execute(name, json.dumps(arguments))


def test_search_uses_effective_price_and_returns_sources(store_tools):
    result = call(store_tools, "search_catalog", category_id=9, max_price_brl="440")
    assert result["ok"]
    products = result["data"]["products"]
    assert any(
        p["product_id"] == 121 and p["price"]["unit_price_brl"] == "439.20" for p in products
    )
    assert all(p["availability"] == "available" and p["source"] for p in products)
    assert call(store_tools, "search_catalog", limit=1)["data"]["truncated"]


def test_search_preserves_matching_and_full_details_remain_available(store_tools):
    result = call(store_tools, "search_catalog", query="nylon", max_price_brl="700")["data"]
    products = result["products"]
    assert products
    for summary in products:
        product = call(store_tools, "get_product", query=str(summary["product_id"]))["data"][
            "product"
        ]
        assert product["specs"]["strings"] == "nylon"
        assert product["description"]
        assert summary["price"] == product["price"]
        assert summary["stock_quantity"] == product["stock_quantity"]
        assert summary["availability"] == product["availability"]
        assert "description" not in summary and "specs" not in summary


def test_conflicting_product_is_flagged_in_search_details_and_quotes(store_tools):
    summary = call(store_tools, "search_catalog", query="Roland Synth 3")["data"]["products"][0]
    product = call(store_tools, "get_product", query="144")["data"]["product"]
    quote = call(store_tools, "quote_product", product_id=144)["data"]
    assert product["name"] == "Teclado Sintetizador Roland Synth 3 Pro"
    assert "Yamaha" in product["description"]
    assert summary["data_quality_notes"] == product["data_quality_notes"]
    assert quote["data_quality_notes"] == product["data_quality_notes"]
    assert "confirm" in quote["data_quality_notes"][0]
    assert not call(store_tools, "get_product", query="81")["data"]["product"]["data_quality_notes"]


def test_unknown_empty_and_ambiguous_products_are_distinct(store_tools):
    assert call(store_tools, "get_product", query="99999")["data"]["status"] == "not_found"
    result = call(store_tools, "get_product", query="Yamaha")["data"]
    assert result["status"] == "ambiguous" and result["requires_clarification"]
    assert len(result["candidates"]) > 1
    result = call(store_tools, "list_categories")["data"]["categories"]
    assert next(c for c in result if c["category_id"] == 6)["product_count"] == 0
    assert call(store_tools, "search_catalog", category_id=6)["data"]["products"] == []


@pytest.mark.parametrize(
    "identifier,availability",
    [(96, "out_of_stock"), (113, "discontinued"), (130, "coming_soon"), (136, "discontinued")],
)
def test_unavailable_product_has_verified_alternatives(store_tools, identifier, availability):
    product = call(store_tools, "get_product", query=str(identifier))["data"]
    assert product["product"]["availability"] == availability
    assert product["alternatives"]
    assert all(p["availability"] == "available" for p in product["alternatives"])
    assert (
        call(store_tools, "quote_product", product_id=identifier)["data"]["status"] == "unavailable"
    )


def test_quote_payment_conditions_and_inactive_promotion(store_tools):
    product = call(store_tools, "get_product", query="Takamine GD20")["data"]
    assert product["promotions"] and not product["promotions"][0]["is_active"]
    quote = call(store_tools, "quote_product", product_id=81, payment_method="credit")["data"]
    assert quote["status"] == "quoted"
    assert quote["price"]["unit_price_brl"] == "599.90"
    plans = quote["payment_terms"]["installment_options"]
    assert next(p for p in plans if p["count"] == 6)["requires_confirmation"]
    assert (
        call(store_tools, "quote_product", product_id=81, quantity=13)["data"]["status"]
        == "insufficient_stock"
    )


@pytest.mark.parametrize(
    "arguments",
    ['{"query":81}', '{"query":"81","extra":true}', "{}", "null", "not JSON", '{"query":" "}'],
)
def test_invalid_product_arguments_are_rejected(store_tools, arguments):
    result = store_tools.execute("get_product", arguments)
    assert not result["ok"] and result["error"] == "invalid_arguments"


@pytest.mark.parametrize("budget", ["NaN", "Infinity", "-1", "0.001", "1,000", "10000001"])
def test_invalid_budget_is_not_used(store_tools, budget):
    assert not call(store_tools, "search_catalog", max_price_brl=budget)["ok"]


def test_integral_json_numbers_are_accepted_but_booleans_are_not(store_tools):
    assert call(store_tools, "quote_product", product_id=81.0, quantity=1.0)["ok"]
    for quantity in (True, 1.5):
        assert not call(store_tools, "quote_product", product_id=81, quantity=quantity)["ok"]


@pytest.mark.parametrize("name", ["get_customer", "get_order", "eval", "__init__", "execute"])
def test_only_allowlisted_tools_can_run(store_tools, name):
    assert store_tools.execute(name, "{}")["error"] == "unknown_tool"


def test_source_errors_do_not_echo_private_details(store_tools, monkeypatch):
    def fail():
        raise ValueError("private-error-details")

    monkeypatch.setattr(store_tools.policies, "context", fail)
    result = store_tools.execute("get_store_policies", "{}")
    assert result["error"] == "source_unavailable"
    assert "private-error-details" not in json.dumps(result)


def test_complete_policies_and_declared_argument_schemas(store_tools):
    result = store_tools.execute("get_store_policies", "{}")
    assert result["ok"] and len(result["data"]["pages"]) == 8
    assert result["data"]["implementation_notes"]
    definitions = tool_definitions()
    assert {tool["name"] for tool in definitions} == set(TOOL_TYPES)
    assert all(
        tool["parameters_json_schema"]["additionalProperties"] is False for tool in definitions
    )
