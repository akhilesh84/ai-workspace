# Nifty Energy Quality Basket MCP Server

> **Stack:** Python · FastMCP · uv

MCP Server exposing the 5-stock quality energy basket valuation strategy as an MCP tool for local AI agents and LLM clients. It scans live market fundamentals directly from exchange feeds (with multi-tier fallback support) and evaluates multi-tier valuation buy-zones to return rebalanced tranche allocations and execution signals.

---

## Basket Constituents

| Ticker | Company Name | Target Weight | Primary Valuation Anchor |
|---|---|---|---|
| `COALINDIA` | Coal India Ltd | 30% | Dividend Yield |
| `POWERGRID` | Power Grid Corp of India | 25% | Price-to-Book (P/B) |
| `PETRONET` | Petronet LNG Ltd | 20% | P/E and P/B |
| `BPCL` | Bharat Petroleum Corp Ltd | 15% | P/B (Troughs only) |
| `CASTROLIND` | Castrol India Ltd | 10% | Price-to-Earnings (P/E) |

---

## Valuation Configuration (`basket_config.json`)

The server decouples all stock definitions, target weights, valuation anchors, and tier thresholds into an external JSON file (`basket_config.json`).

### Hot-Reloading
The configuration is loaded dynamically on each tool call (`evaluate_energy_basket`). **Any edits made to the configuration file take effect immediately on the next execution without needing to restart the MCP server.**

### Path Resolution Priority

When looking for the configuration file, the server searches the following locations in priority order:

| Priority | Location | Description |
|:---:|---|---|
| **1 (Highest)** | `BASKET_CONFIG_PATH` | Environment variable pointing to an absolute or relative custom JSON file path. |
| **2** | `<server_root>/config/basket_config.json` | Standard project configuration file (recommended for local editing). |
| **3** | `<server_root>/src/server/config/basket_config.json` | Package-level configuration directory. |
| **4** | `<server_root>/src/server/tools/config/basket_config.json` | Tools-level configuration directory. |
| **5** | `<server_root>/src/server/basket_config.json` | Server module root file. |
| **Fallback** | *Embedded Defaults* | Hardcoded `DEFAULT_BASKET_CONFIG` used as safety fallback if no file exists or if JSON is invalid. |

### Configuration File Schema

Each entry in `basket_config.json` maps a stock symbol to its parameters:

```json
{
  "COALINDIA": {
    "name": "Coal India Ltd",
    "target_weight": 0.30,
    "primary_anchor": "div_yield",
    "tiers": {
      "tier_1_sip":      { "pe_max": 8.2,  "pb_max": 2.20, "yield_min": 6.2 },
      "tier_2_aggr":     { "pe_max": 7.2,  "pb_max": 1.90, "yield_min": 7.0 },
      "tier_3_lump_sum": { "pe_max": 6.2,  "pb_max": 1.65, "yield_min": 7.8 },
      "pause_above":     { "pe_min": 9.8,  "pb_min": 2.75, "yield_max": 5.0 }
    }
  }
}
```

### Parameter Explanations

- **`target_weight`**: Baseline portfolio allocation decimal (sum of all constituents must equal `1.0`).
- **`primary_anchor`**:
  - `"div_yield"`: Uses dividend yield as primary accumulation criteria.
  - `"pb"`: Uses Price-to-Book as primary multiple.
  - `"pe_and_pb"`: Requires both P/E and P/B multiple constraints.
  - `"pb_only_on_troughs"`: Specifically checks P/B floors during cyclical earnings contractions (e.g. BPCL).
  - `"pe"`: Uses Price-to-Earnings as primary multiple.
- **Valuation Tiers:**
  - **`tier_1_sip` (1.0x):** Fair value accumulation zone.
  - **`tier_2_aggr` (2.0x):** Undervalued multiple zone; doubles systematic allocation.
  - **`tier_3_lump_sum` (3.0x):** Deep value floor breached; triggers reserve deployment.
  - **`pause_above` (0.0x):** Multiple expanded beyond cyclical threshold; redirects capital into liquid cash reserves.

---

## Tools Exposed

| Tool | Description | Parameters |
|---|---|---|
| `evaluate_energy_basket` | Scans live market multiples, evaluates valuation buy-zones against `basket_config.json`, and returns exact rupee tranches and execution signals. | `monthly_budget: float = 25000.0` |

### Sample Response

```json
{
  "status": "success",
  "monthly_budget_inr": 50000.0,
  "is_live_data": true,
  "config_source": ".../mcp-servers/nifty-energy-basket/v1/config/basket_config.json",
  "allocations": {
    "BPCL": {
      "name": "Bharat Petroleum Corp Ltd",
      "price": 293.0,
      "pe": 9.07,
      "pb": 1.25,
      "div_yield": 5.97,
      "signal": "TIER 2 (AGGRESSIVE)",
      "multiplier": 2.0,
      "target_weight_pct": 26.09,
      "monthly_tranche_inr": 13043.48,
      "notes": "Undervalued zone. Double SIP allocation (2.0x).",
      "is_live": true,
      "data_source": "Screener.in (Live)"
    }
  },
  "paused_pool_redirected_inr": 0.0
}
```

---

## Running Locally

```bash
cd mcp-servers/nifty-energy-basket/latest
uv sync
uv run serve
```

Or run directly via Python:
```bash
python NiftyEnergyMCPServer.py
```

---

## Client Configurations

Add to your MCP configuration file (`mcp_config.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nifty-energy-basket": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/akhilesh/MyDevArea/ai-workspace/mcp-servers/nifty-energy-basket/latest",
        "run",
        "serve"
      ]
    }
  }
}
```

### Custom Config Path via Environment Variable

To instruct the MCP server process to load an alternate config file:

```json
{
  "mcpServers": {
    "nifty-energy-basket": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/akhilesh/MyDevArea/ai-workspace/mcp-servers/nifty-energy-basket/latest",
        "run",
        "serve"
      ],
      "env": {
        "BASKET_CONFIG_PATH": "/path/to/custom_basket_config.json"
      }
    }
  }
}
```
