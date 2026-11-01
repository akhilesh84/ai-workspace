# Nifty Energy Quality Basket MCP Server

> **Stack:** Python · FastMCP · uv

MCP Server exposing the 5-stock quality energy basket valuation strategy as an MCP tool for local AI agents and LLM clients. It scans live Yahoo Finance fundamentals (or graceful fallbacks) and evaluates multi-tier valuation buy-zones to return tranche allocations and execution signals.

## Basket Constituents

| Ticker | Company Name | Target Weight | Primary Valuation Anchor |
|--------|--------------|---------------|--------------------------|
| `COALINDIA` | Coal India Ltd | 30% | Dividend Yield |
| `POWERGRID` | Power Grid Corp of India | 25% | Price-to-Book (P/B) |
| `PETRONET` | Petronet LNG Ltd | 20% | P/E and P/B |
| `BPCL` | Bharat Petroleum Corp Ltd | 15% | P/B (Troughs only) |
| `CASTROLIND` | Castrol India Ltd | 10% | Price-to-Earnings (P/E) |

## Tools Exposed

| Tool | Description | Parameters |
|------|-------------|------------|
| `evaluate_energy_basket` | Evaluates 3-tier valuation buy-zones (Tier 1 SIP Accumulate, Tier 2 Aggressive, Tier 3 Lump Sum, Pause/Trim) and calculates dynamic monthly INR capital allocations and redirected pause pool. | `monthly_budget: float = 25000.0` |

### Valuation Tiers
- **Tier 1 (SIP Accumulate - 1.0x):** Fair value accumulation zone.
- **Tier 2 (Aggressive - 2.0x):** Undervalued multiple zone; double SIP tranche.
- **Tier 3 (Lump Sum - 3.0x):** Deep value floor breached; deploy strategic reserves.
- **Pause / Trim (0.0x):** Multiple expanded beyond cyclical threshold; tranches redirected to pause reserve pool.

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

## Running in AI Clients

### Google Antigravity / Claude Desktop / VS Code Copilot

Add to your MCP configuration file:

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
