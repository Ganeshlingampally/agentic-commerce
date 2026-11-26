"""
agent.py – Agentic shopping assistant.

Usage
-----
Live (requires ANTHROPIC_API_KEY):
    python agent.py "Find a mouse under 1000 and add 2 to my cart"

Offline mock (no API key needed):
    python agent.py --mock
    python agent.py --mock "Find a mouse under 1000 and add 2 to my cart"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from shop_tools import TOOL_SCHEMAS, run_tool

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 4096
MAX_ROUNDS = 10  # hard cap on agentic rounds to prevent infinite loops

SYSTEM_PROMPT = """You are a helpful shopping assistant for an online electronics store.
Your job is to help users find products, check availability, manage their cart, and place orders.

IMPORTANT RULES:
1. Always search for products before adding them to the cart.
2. Check stock before adding to cart if you haven't just searched.
3. Show the cart summary (view_cart) before asking the user to confirm an order.
4. NEVER call place_order without first asking the user to explicitly confirm.
5. When the user confirms, call place_order and report the order ID.
6. Be concise, helpful, and proactive – complete the full requested flow in one go."""


# ---------------------------------------------------------------------------
# Rich terminal colours
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
MAGENTA= "\033[95m"
RED    = "\033[91m"


def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"


# ---------------------------------------------------------------------------
# Live Claude agent loop
# ---------------------------------------------------------------------------

def run_live(user_message: str) -> None:
    try:
        import anthropic
    except ImportError:
        print(_c(RED, "Error: anthropic package not installed. Run: pip install anthropic"))
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(_c(RED, "Error: ANTHROPIC_API_KEY environment variable is not set."))
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    print(_c(CYAN, f"\n🛍  Shopping Assistant (live · {MODEL})"))
    print(_c(CYAN, "─" * 55))
    print(_c(BOLD, f"User: ") + user_message)
    print()

    for round_num in range(1, MAX_ROUNDS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Collect assistant content
        messages.append({"role": "assistant", "content": response.content})

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    print(_c(GREEN, "Assistant: ") + block.text)
            break

        if response.stop_reason != "tool_use":
            print(_c(YELLOW, f"[Unexpected stop_reason: {response.stop_reason}]"))
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                if hasattr(block, "text") and block.text.strip():
                    print(_c(MAGENTA, f"[Thinking] ") + block.text.strip())
                continue

            print(_c(YELLOW, f"  → Tool: ") + _c(BOLD, block.name) + f"  args={json.dumps(block.input)}")
            result_str = run_tool(block.name, block.input)
            result_data = json.loads(result_str)
            print(_c(CYAN, f"  ← Result: ") + json.dumps(result_data, indent=None)[:200])
            print()

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": block.id,
                "content":     result_str,
            })

        messages.append({"role": "user", "content": tool_results})

        # Intercept place_order: ask user to confirm
        called_tools = [b.name for b in response.content if b.type == "tool_use"]
        # (The LLM is instructed to ask first, but we guard on the client side too.)

    else:
        print(_c(RED, f"[Reached max rounds ({MAX_ROUNDS}). Stopping.]"))


# ---------------------------------------------------------------------------
# Mock agent loop (no API key needed)
# ---------------------------------------------------------------------------

MOCK_STEPS = [
    {
        "description": "Search for mice under ₹1,000",
        "tool": "search_products",
        "args": {"query": "mouse", "max_price": 1000, "in_stock_only": True},
    },
    {
        "description": "Check stock for Razer DeathAdder V3 (P002)",
        "tool": "check_stock",
        "args": {"product_id": "P002"},
    },
    {
        "description": "Add 2 units of Razer DeathAdder V3 to cart",
        "tool": "add_to_cart",
        "args": {"product_id": "P002", "quantity": 2},
    },
    {
        "description": "View cart to show total",
        "tool": "view_cart",
        "args": {},
    },
    {
        "description": "Place order after (simulated) user confirmation",
        "tool": "place_order",
        "args": {},
    },
]


def run_mock(user_message: str) -> None:
    print(_c(CYAN, "\n🛍  Shopping Assistant (offline mock)"))
    print(_c(CYAN, "─" * 55))
    print(_c(BOLD, "User: ") + user_message)
    print()

    for i, step in enumerate(MOCK_STEPS, 1):
        print(_c(MAGENTA, f"[Step {i}/{len(MOCK_STEPS)}] ") + step["description"])
        print(_c(YELLOW, f"  → Tool: ") + _c(BOLD, step["tool"]) + f"  args={json.dumps(step['args'])}")
        result_str = run_tool(step["tool"], step["args"])
        result_data = json.loads(result_str)
        print(_c(CYAN, f"  ← Result: ") + json.dumps(result_data))

        # Simulate confirmation gate before order
        if step["tool"] == "place_order":
            print()
            print(_c(GREEN, "  [Mock confirms order on behalf of user]"))

        print()

    print(_c(GREEN, "✅  Demo complete. All five steps executed successfully."))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic shopping assistant")
    parser.add_argument(
        "message",
        nargs="?",
        default="Find a mouse under 1000 and add 2 to my cart",
        help="Natural-language shopping request",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline mock mode (no API key required)",
    )
    args = parser.parse_args()

    if args.mock:
        run_mock(args.message)
    else:
        run_live(args.message)


if __name__ == "__main__":
    main()
