"""
test_shop_tools.py – Unit tests for shop_tools.py

Run with:  pytest -q
"""

from __future__ import annotations

import json
import importlib
import types

import pytest

# We reimport shop_tools fresh for each test to get a clean in-memory state.
import shop_tools


def _fresh():
    """Return a freshly-reloaded shop_tools module so each test is isolated."""
    return importlib.reload(shop_tools)


# ---------------------------------------------------------------------------
# Test 1 – search_products
# ---------------------------------------------------------------------------

class TestSearchProducts:
    def test_search_by_keyword_returns_results(self):
        st = _fresh()
        raw = st.search_products("mouse")
        data = json.loads(raw)
        assert "results" in data
        assert len(data["results"]) >= 2

    def test_max_price_filter(self):
        st = _fresh()
        raw = st.search_products("mouse", max_price=600)
        data = json.loads(raw)
        for item in data["results"]:
            assert item["price"] <= 600

    def test_out_of_stock_excluded_by_default(self):
        st = _fresh()
        raw = st.search_products("mouse", in_stock_only=True)
        data = json.loads(raw)
        for item in data["results"]:
            assert item["stock"] > 0

    def test_no_match_returns_empty(self):
        st = _fresh()
        raw = st.search_products("quantum toaster")
        data = json.loads(raw)
        assert data["results"] == []


# ---------------------------------------------------------------------------
# Test 2 – check_stock
# ---------------------------------------------------------------------------

class TestCheckStock:
    def test_known_product(self):
        st = _fresh()
        raw = st.check_stock("P001")
        data = json.loads(raw)
        assert data["product_id"] == "P001"
        assert data["stock"] >= 0

    def test_unknown_product(self):
        st = _fresh()
        raw = st.check_stock("P999")
        data = json.loads(raw)
        assert "error" in data


# ---------------------------------------------------------------------------
# Test 3 – add_to_cart
# ---------------------------------------------------------------------------

class TestAddToCart:
    def test_add_valid_item(self):
        st = _fresh()
        raw = st.add_to_cart("P001", 1)
        data = json.loads(raw)
        assert data["success"] is True
        assert data["added"]["qty"] == 1

    def test_add_accumulates_qty(self):
        st = _fresh()
        st.add_to_cart("P001", 2)
        raw = st.add_to_cart("P001", 3)
        data = json.loads(raw)
        assert data["added"]["qty"] == 5

    def test_out_of_stock_blocked(self):
        st = _fresh()
        raw = st.add_to_cart("P005", 1)   # P005 has stock=0
        data = json.loads(raw)
        assert "error" in data

    def test_exceeds_stock_blocked(self):
        st = _fresh()
        raw = st.add_to_cart("P002", 9999)
        data = json.loads(raw)
        assert "error" in data

    def test_zero_quantity_rejected(self):
        st = _fresh()
        raw = st.add_to_cart("P001", 0)
        data = json.loads(raw)
        assert "error" in data


# ---------------------------------------------------------------------------
# Test 4 – view_cart
# ---------------------------------------------------------------------------

class TestViewCart:
    def test_empty_cart(self):
        st = _fresh()
        data = json.loads(st.view_cart())
        assert data["total"] == 0
        assert data["items"] == []

    def test_view_after_add(self):
        st = _fresh()
        st.add_to_cart("P001", 2)   # 2 × 799 = 1598
        data = json.loads(st.view_cart())
        assert data["total"] == 1598
        assert len(data["items"]) == 1


# ---------------------------------------------------------------------------
# Test 5 – place_order
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    def test_place_order_success(self):
        st = _fresh()
        st.add_to_cart("P002", 1)
        data = json.loads(st.place_order())
        assert data["success"] is True
        assert "order_id" in data
        # Cart should be cleared after order
        cart_data = json.loads(st.view_cart())
        assert cart_data["total"] == 0

    def test_place_order_empty_cart(self):
        st = _fresh()
        data = json.loads(st.place_order())
        assert "error" in data

    def test_stock_decremented_after_order(self):
        st = _fresh()
        # P004 starts with stock=42
        st.add_to_cart("P004", 5)
        st.place_order()
        stock_data = json.loads(st.check_stock("P004"))
        assert stock_data["stock"] == 37


# ---------------------------------------------------------------------------
# Test 6 – run_tool dispatcher
# ---------------------------------------------------------------------------

class TestRunTool:
    def test_dispatches_known_tool(self):
        st = _fresh()
        raw = st.run_tool("check_stock", {"product_id": "P001"})
        data = json.loads(raw)
        assert "stock" in data

    def test_unknown_tool_returns_error(self):
        st = _fresh()
        raw = st.run_tool("nonexistent_tool", {})
        data = json.loads(raw)
        assert "error" in data
