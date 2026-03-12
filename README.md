# Stock Trading Agents

An autonomous multi-agent stock trading system built with the **OpenAI Agents SDK** and **Model Context Protocol (MCP)**. Each trader is an AI agent that researches the market, makes investment decisions, and executes real trades — all without human intervention.

---

## How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                     Trader Agent                    │
│  (persona, strategy, portfolio management)          │
│                                                     │
│   ┌─────────────┐   ┌────────────┐  ┌───────────┐  │
│   │  Researcher │   │  Accounts  │  │  Market   │  │
│   │    Tool     │   │   Server   │  │  Server   │  │
│   │  (sub-agent)│   │   (MCP)    │  │   (MCP)   │  │
│   └──────┬──────┘   └─────┬──────┘  └─────┬─────┘  │
│          │                │               │         │
└──────────┼────────────────┼───────────────┼─────────┘
           │                │               │
   ┌───────▼──────┐  ┌──────▼─────┐  ┌─────▼──────┐
   │ Brave Search │  │  SQLite DB │  │ Polygon.io │
   │  + Web Fetch │  │ (accounts) │  │  (prices)  │
   │  + Memory DB │  └────────────┘  └────────────┘
   └──────────────┘
```

### Agents

**Trader Agent** (`trader.py`)
The top-level agent. It has a name, a personality, and an investment strategy stored in the database. On each cycle it:
1. Reads its current account balance, holdings, and strategy.
2. Calls the **Researcher** sub-agent to gather market intelligence.
3. Uses market data tools to look up live prices.
4. Decides whether to buy, sell, or hold.
5. Executes trades via the Accounts MCP server.
6. Sends a push notification summarising what it did.

The trader alternates between two modes each run:
- **Trade mode** — find new opportunities and open/close positions.
- **Rebalance mode** — review the existing portfolio and trim or top up as needed.

**Researcher Agent** (`trader.py` → `get_researcher`)
A sub-agent surfaced to the Trader as a single `Researcher` tool. It has access to:
- **Brave Search** — web search for financial news.
- **mcp-server-fetch** — fetch and read arbitrary web pages.
- **mcp-memory-libsql** — a persistent per-trader knowledge graph stored in a local SQLite file under `memory/<name>.db`. The researcher stores entities (companies, tickers, URLs) here and recalls them on future runs, building expertise over time.

### MCP Servers

The project uses the [Model Context Protocol](https://modelcontextprotocol.io) to expose tools and resources to agents via stdio subprocesses.

| Server | File | Purpose |
|---|---|---|
| `accounts_server` | `accounts_server.py` | Buy/sell shares, read balances and holdings, change strategy |
| `market_server` | `market_server.py` | Look up end-of-day share prices (free Polygon tier) |
| `push_server` | `push_server.py` | Send Pushover push notifications |
| `mcp_polygon` | (external, via uvx) | Full Polygon.io data — snapshots, technicals, fundamentals (paid/realtime tiers) |
| `mcp-server-fetch` | (external, via uvx) | Fetch web pages |
| `@modelcontextprotocol/server-brave-search` | (external, via npx) | Brave Search API |
| `mcp-memory-libsql` | (external, via npx) | Persistent knowledge graph per trader |

### Data Layer

`database.py` and `accounts.py` manage a local SQLite database (`accounts.db`) with three tables:

- **accounts** — each trader's balance, holdings, strategy, and full transaction history.
- **logs** — append-only audit log of every buy, sell, and account read.
- **market** — cached end-of-day prices keyed by date (avoids redundant Polygon API calls).

`accounts.py` also enforces a 0.2% bid/ask spread on all trades (`SPREAD = 0.002`) to simulate realistic execution costs.

### Market Data

`market.py` supports three Polygon.io tiers, controlled by the `POLYGON_PLAN` environment variable:

| Plan | Data | Notes |
|---|---|---|
| `free` (default) | Previous-day close prices | Cached in SQLite; bulk-fetched once per day |
| `paid` | 15-minute delayed snapshot | Per-ticker lookup |
| `realtime` | Live last-trade price | Per-ticker lookup |

If no Polygon API key is set the system falls back to random prices (useful for smoke-testing without an API key).

### Multi-Model Support

`get_model()` in `trader.py` routes to the correct provider based on the model name string:

- OpenRouter models (`"org/model"` format) → OpenRouter
- `"deepseek-*"` → DeepSeek
- `"grok-*"` → xAI
- `"gemini-*"` → Google Gemini
- Everything else → OpenAI directly (e.g. `"gpt-4o-mini"`)

This lets you run different traders on different models simply by changing `model_name` when constructing a `Trader`.

### Tracing

Every trader run is wrapped in an OpenAI Agents SDK `trace()` context (`tracers.py`). The trace ID is derived deterministically from the trader's name (SHA-256 → UUID), so all runs for the same trader are grouped together in the tracing dashboard.

---

## Project Structure

```
.
├── trader.py            # Trader class + Researcher agent factory
├── templates.py         # System prompts and message templates
├── mcp_params.py        # MCP server parameter definitions
├── accounts.py          # Account model (Pydantic) — trade logic, P&L
├── accounts_server.py   # MCP server exposing account tools + resources
├── accounts_client.py   # MCP client helpers for reading account data
├── market.py            # Polygon.io market data (3 tiers)
├── market_server.py     # MCP server exposing share-price lookup
├── push_server.py       # MCP server for Pushover notifications
├── database.py          # SQLite helpers (accounts, logs, market cache)
├── tracers.py           # Deterministic trace ID generation
├── pyproject.toml       # Python project / dependency declaration
├── .env.example         # Environment variable template
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js + npx (for the Brave Search and memory MCP servers)
- API keys — see `.env.example`

### Installation

```bash
git clone https://github.com/<your-username>/stock-trading-agents.git
cd stock-trading-agents

# Install Python dependencies
uv sync
# or: pip install -e .

# Copy and fill in your API keys
cp .env.example .env
```

### Running a Trader

```python
import asyncio
from trader import Trader

trader = Trader(name="Alice", model_name="gpt-4o-mini")
asyncio.run(trader.run())
```

Or set a custom strategy first via the accounts server, then call `trader.run()` in a loop or on a scheduler (e.g. cron, APScheduler).

### Resetting an Account

```python
from accounts import Account

account = Account.get("Alice")
account.reset(strategy="Focus on US large-cap tech stocks with strong earnings momentum.")
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (default model) | OpenAI API key |
| `DEEPSEEK_API_KEY` | Optional | DeepSeek API key |
| `GOOGLE_API_KEY` | Optional | Google Gemini API key |
| `GROK_API_KEY` | Optional | xAI Grok API key |
| `OPENROUTER_API_KEY` | Optional | OpenRouter API key |
| `POLYGON_API_KEY` | Optional | Polygon.io API key |
| `POLYGON_PLAN` | Optional | `free` / `paid` / `realtime` (default: `free`) |
| `BRAVE_API_KEY` | Yes (researcher) | Brave Search API key |
| `PUSHOVER_USER` | Optional | Pushover user key |
| `PUSHOVER_TOKEN` | Optional | Pushover app token |

---

## Key Design Decisions

- **MCP over direct function calls** — each capability (accounts, market data, push) is an independent subprocess. This makes it easy to swap implementations (e.g. replace the free market server with the paid Polygon MCP) without touching agent code.
- **Researcher as a tool** — rather than giving the trader raw search tools, the researcher is a full sub-agent exposed via `agent.as_tool()`. This lets it do multi-step research (search → read → cross-reference) before returning a clean summary.
- **Persistent memory per trader** — the researcher's knowledge graph is stored per-trader in `memory/<name>.db`, so insights compound across runs.
- **Alternating trade/rebalance cycles** — separating opportunity-seeking from portfolio maintenance keeps each run focused and reduces over-trading.
- **Spread simulation** — a 0.2% spread on every trade discourages excessive churn and produces more realistic P&L figures.

---

## License

MIT
