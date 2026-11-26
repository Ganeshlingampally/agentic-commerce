"""
shop_tools.py – Tool implementations for the agentic shopping assistant.

Each function maps 1-to-1 with an Anthropic tool definition.
They share a simple in-memory "database" so the agent loop can call them
in any order and state persists within a session.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# In-memory "database"
# ---------------------------------------------------------------------------

_PRODUCTS: list[dict[str, Any]] = [
    {"id": "P001", "name": "Logitech MX Master 3S Mouse",   "price": 799,  "category": "mouse", "stock": 15},
    {"id": "P002", "name": "Razer DeathAdder V3 Mouse",      "price": 549,  "category": "mouse", "stock": 8},
    {"id": "P003", "name": "Apple Magic Mouse",               "price": 6900, "category": "mouse", "stock": 5},
    {"id": "P004", "name": "HP X1500 Wired Mouse",            "price": 349,  "category": "mouse", "stock": 42},
    {"id": "P005", "name": "Corsair Dark Core RGB Mouse",     "price": 899,  "category": "mouse", "stock": 0},  # out of stock
    {"id": "P006", "name": "Mechanical Keyboard TKL",         "price": 2499, "category": "keyboard", "stock": 10},
    {"id": "P007", "name": "USB-C Hub 7-in-1",                "price": 1299, "category": "accessories", "stock": 20},
]

_cart: dict[str, dict[str, Any]] = {}   # product_id -> {product, qty}
_orders: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Tool: search_products
# ---------------------------------------------------------------------------

def search_products(query: str, max_price: float | None = None, in_stock_only: bool = True) -> str:
    """Search the product catalogue and return matching items as JSON."""
    results = []
    q = query.lower()
    for p in _PRODUCTS:
        if q not in p["name"].lower() and q not in p["category"].lower():
            continue
        if in_stock_only and p["stock"] == 0:
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        results.append({
            "id":       p["id"],
            "name":     p["name"],
            "price":    p["price"],
            "stock":    p["stock"],
            "category": p["category"],
        })
    if not results:
        return json.dumps({"results": [], "message": "No products found matching your criteria."})
    return json.dumps({"results": results})


# ---------------------------------------------------------------------------
# Tool: check_stock
# ---------------------------------------------------------------------------

def check_stock(product_id: str) -> str:
    """Return current stock level for a product."""
    for p in _PRODUCTS:
        if p["id"] == product_id:
            return json.dumps({"product_id": product_id, "name": p["name"], "stock": p["stock"]})
    return json.dumps({"error": f"Product {product_id!r} not found."})


# ---------------------------------------------------------------------------
# Tool: add_to_cart
# ---------------------------------------------------------------------------

def add_to_cart(product_id: str, quantity: int) -> str:
    """Add *quantity* units of a product to the cart."""
    if quantity < 1:
        return json.dumps({"error": "Quantity must be at least 1."})
    for p in _PRODUCTS:
        if p["id"] == product_id:
            if p["stock"] == 0:
                return json.dumps({"error": f"{p['name']!r} is out of stock."})
            if quantity > p["stock"]:
                return json.dumps({
                    "error": f"Only {p['stock']} units of {p['name']!r} available."
                })
            if product_id in _cart:
                _cart[product_id]["qty"] += quantity
            else:
                _cart[product_id] = {"product": p, "qty": quantity}
            return json.dumps({
                "success": True,
                "added":   {"id": product_id, "name": p["name"], "qty": _cart[product_id]["qty"]},
            })
    return json.dumps({"error": f"Product {product_id!r} not found."})


# ---------------------------------------------------------------------------
# Tool: view_cart
# ---------------------------------------------------------------------------

def view_cart() -> str:
    """Return the current cart contents and total price."""
    if not _cart:
        return json.dumps({"items": [], "total": 0, "message": "Cart is empty."})
    items = []
    total = 0
    for pid, entry in _cart.items():
        subtotal = entry["product"]["price"] * entry["qty"]
        total += subtotal
        items.append({
            "id":       pid,
            "name":     entry["product"]["name"],
            "price":    entry["product"]["price"],
            "qty":      entry["qty"],
            "subtotal": subtotal,
        })
    return json.dumps({"items": items, "total": total})


# ---------------------------------------------------------------------------
# Tool: place_order
# ---------------------------------------------------------------------------

def place_order() -> str:
    """Finalise the order. The agent MUST ask the user to confirm before calling this."""
    global _cart
    if not _cart:
        return json.dumps({"error": "Cannot place an order: cart is empty."})
    # Deduct stock
    for pid, entry in _cart.items():
        for p in _PRODUCTS:
            if p["id"] == pid:
                p["stock"] -= entry["qty"]
    order = {
        "order_id":  str(uuid.uuid4())[:8].upper(),
        "items":     list(_cart.values()),
        "total":     sum(e["product"]["price"] * e["qty"] for e in _cart.values()),
        "status":    "confirmed",
    }
    _orders.append(order)
    _cart = {}
    return json.dumps({
        "success":  True,
        "order_id": order["order_id"],
        "total":    order["total"],
        "message":  f"Order {order['order_id']} placed successfully! Total: ₹{order['total']:,}",
    })


# ---------------------------------------------------------------------------
# Tool: clear_cart  (utility – handy for tests)
# ---------------------------------------------------------------------------

def clear_cart() -> str:
    """Empty the cart without placing an order."""
    global _cart
    _cart = {}
    return json.dumps({"success": True, "message": "Cart cleared."})


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "Search the product catalogue. Returns matching products with IDs, "
            "names, prices and stock levels."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":        {"type": "string",  "description": "Keyword or category to search for"},
                "max_price":    {"type": "number",  "description": "Upper price limit (inclusive)"},
                "in_stock_only":{"type": "boolean", "description": "If true, exclude out-of-stock items (default true)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_stock",
        "description": "Check current stock level for a specific product ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The product ID, e.g. P001"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "add_to_cart",
        "description": "Add a product to the shopping cart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string",  "description": "The product ID to add"},
                "quantity":   {"type": "integer", "description": "Number of units to add (minimum 1)"},
            },
            "required": ["product_id", "quantity"],
        },
    },
    {
        "name": "view_cart",
        "description": "View all items currently in the cart along with the total price.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "place_order",
        "description": (
            "Place the order for everything currently in the cart. "
            "IMPORTANT: you MUST ask the user to confirm before calling this tool."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "clear_cart",
        "description": "Remove all items from the cart without placing an order.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Dispatch helper
# ---------------------------------------------------------------------------

TOOL_FN_MAP = {
    "search_products": search_products,
    "check_stock":     check_stock,
    "add_to_cart":     add_to_cart,
    "view_cart":       view_cart,
    "place_order":     place_order,
    "clear_cart":      clear_cart,
}


def run_tool(name: str, inputs: dict[str, Any]) -> str:
    """Dispatch a tool call by name and return its JSON string result."""
    fn = TOOL_FN_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name!r}"})
    return fn(**inputs)
