# Agentic Commerce – Shopping Assistant

A terminal-based agentic shopping assistant that uses **Claude's tool-calling API** to autonomously plan and execute a multi-step purchase flow.

## What it does

The LLM drives a complete shopping session on its own:

| Step | Tool | Description |
|------|------|-------------|
| 1 | `search_products` | Finds products matching the user's request (keyword + price filter) |
| 2 | `check_stock` | Verifies availability before adding to cart |
| 3 | `add_to_cart` | Adds the chosen items with the requested quantity |
| 4 | `view_cart` | Shows a full cart summary with subtotals and total |
| 5 | `place_order` | Finalises the order – **only after explicit user confirmation** |

The agent loop runs for up to 10 rounds, feeding tool results back to Claude until `stop_reason == "end_turn"`.

## Project layout

```
agentic-commerce/
├── agent.py          # Agentic loop (live Claude API + --mock offline mode)
├── shop_tools.py     # Tool implementations & Anthropic schemas
├── test_shop_tools.py# pytest unit tests
├── requirements.txt
└── README.md
```

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run offline demo (no API key needed)
python agent.py --mock
python agent.py --mock "Find a keyboard under 3000 and add 1 to my cart"

# 3. Run with live Claude API
export ANTHROPIC_API_KEY=sk-ant-...        # Windows: $Env:ANTHROPIC_API_KEY="sk-ant-..."
python agent.py "Find a mouse under 1000 and add 2 to my cart"

# 4. Run unit tests
pytest -q
```

## Architecture

```
User prompt
    │
    ▼
agent.py ──► Claude claude-sonnet-4-5
                │  (tool_use blocks)
                ▼
         shop_tools.py
         ┌─────────────────────┐
         │ search_products      │
         │ check_stock          │  ◄── in-memory product DB
         │ add_to_cart          │  ◄── in-memory cart
         │ view_cart            │
         │ place_order          │
         │ clear_cart           │
         └─────────────────────┘
                │  (tool_result)
                ▼
         Claude generates next action
         … repeat until end_turn …
                │
                ▼
         Final natural-language response to user
```

## Safety

- `place_order` is guarded by an explicit system-prompt instruction *and* a mock confirmation gate in the agent loop.
- The agent will never order without the user typing a confirmation.

## Running tests

```
pytest -v
```

Expected output: **18 tests passed**.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Live mode only | Your Claude API key |

## Tech stack

- Python 3.10+
- [Anthropic Python SDK](https://github.com/anthropic/anthropic-sdk-python) ≥ 0.30
- pytest ≥ 8
