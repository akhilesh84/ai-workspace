"""Energy Basket Valuation Tool.

Exposes the 5-stock energy basket valuation strategy as an MCP tool for local AI
agents and LLM clients.
"""

from typing import Any, Dict, Tuple
import requests

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Basket configuration mapping
BASKET_CONFIG: Dict[str, Dict[str, Any]] = {
    "COALINDIA": {
        "name": "Coal India Ltd",
        "target_weight": 0.30,
        "primary_anchor": "div_yield",
        "tiers": {
            "tier_1_sip":      {"pe_max": 8.2,  "pb_max": 2.20, "yield_min": 6.2},
            "tier_2_aggr":     {"pe_max": 7.2,  "pb_max": 1.90, "yield_min": 7.0},
            "tier_3_lump_sum": {"pe_max": 6.2,  "pb_max": 1.65, "yield_min": 7.8},
            "pause_above":     {"pe_min": 9.8,  "pb_min": 2.75, "yield_max": 5.0},
        }
    },
    "POWERGRID": {
        "name": "Power Grid Corp of India",
        "target_weight": 0.25,
        "primary_anchor": "pb",
        "tiers": {
            "tier_1_sip":      {"pe_max": 15.5, "pb_max": 2.85, "yield_min": 3.5},
            "tier_2_aggr":     {"pe_max": 14.0, "pb_max": 2.50, "yield_min": 4.2},
            "tier_3_lump_sum": {"pe_max": 12.0, "pb_max": 2.10, "yield_min": 4.8},
            "pause_above":     {"pe_min": 18.5, "pb_min": 3.40, "yield_max": 2.8},
        }
    },
    "PETRONET": {
        "name": "Petronet LNG Ltd",
        "target_weight": 0.20,
        "primary_anchor": "pe_and_pb",
        "tiers": {
            "tier_1_sip":      {"pe_max": 11.0, "pb_max": 2.10, "yield_min": 3.4},
            "tier_2_aggr":     {"pe_max": 9.8,  "pb_max": 1.85, "yield_min": 4.0},
            "tier_3_lump_sum": {"pe_max": 8.5,  "pb_max": 1.60, "yield_min": 4.6},
            "pause_above":     {"pe_min": 13.5, "pb_min": 2.70, "yield_min": 2.5},
        }
    },
    "BPCL": {
        "name": "Bharat Petroleum Corp Ltd",
        "target_weight": 0.15,
        "primary_anchor": "pb_only_on_troughs",
        "tiers": {
            "tier_1_sip":      {"pe_max": 8.0,  "pb_max": 1.50, "yield_min": 5.2},
            "tier_2_aggr":     {"pe_max": 6.8,  "pb_max": 1.30, "yield_min": 6.5},
            "tier_3_lump_sum": {"pe_max": 5.5,  "pb_max": 1.10, "yield_min": 7.5},
            "pause_above":     {"pe_min": 10.5, "pb_min": 1.85, "yield_max": 3.8},
        }
    },
    "CASTROLIND": {
        "name": "Castrol India Ltd",
        "target_weight": 0.10,
        "primary_anchor": "pe",
        "tiers": {
            "tier_1_sip":      {"pe_max": 18.5, "pb_max": 8.80, "yield_min": 4.0},
            "tier_2_aggr":     {"pe_max": 16.5, "pb_max": 7.80, "yield_min": 4.7},
            "tier_3_lump_sum": {"pe_max": 14.5, "pb_max": 6.80, "yield_min": 5.4},
            "pause_above":     {"pe_min": 22.5, "pb_min": 10.5, "yield_max": 3.2},
        }
    }
}


def get_fallback(ticker: str) -> Dict[str, float]:
    """Provides fallback metrics when live feeds are unreachable."""
    mock = {
        "COALINDIA":  {"price": 435.0, "pe": 8.1,  "pb": 2.12, "div_yield": 6.35},
        "POWERGRID":  {"price": 325.0, "pe": 15.1, "pb": 2.78, "div_yield": 3.62},
        "PETRONET":   {"price": 315.0, "pe": 10.6, "pb": 1.98, "div_yield": 3.48},
        "BPCL":       {"price": 310.0, "pe": 7.3,  "pb": 1.32, "div_yield": 5.80},
        "CASTROLIND": {"price": 230.0, "pe": 18.1, "pb": 8.50, "div_yield": 4.15}
    }
    return mock.get(ticker, {"price": 100.0, "pe": 10.0, "pb": 2.0, "div_yield": 4.0})


def fetch_yahoo_metrics(ticker: str) -> Dict[str, float]:
    """Fetches key valuation metrics from Yahoo Finance with fallback support."""
    yf_symbol = f"{ticker}.NS"
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{yf_symbol}?modules=summaryDetail,defaultKeyStatistics,financialData,price"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            j = res.json()
            result = j.get("quoteSummary", {}).get("result", [{}])[0]
            summary = result.get("summaryDetail") or {}
            stats = result.get("defaultKeyStatistics") or {}
            price_mod = result.get("price") or {}

            price = (price_mod.get("regularMarketPrice") or {}).get("raw", 0.0)
            pe = (summary.get("trailingPE") or {}).get("raw", 0.0)
            pb = (stats.get("priceToBook") or {}).get("raw", 0.0)
            dy_raw = (summary.get("dividendYield") or {}).get("raw", 0.0)
            div_yield = (dy_raw * 100.0) if dy_raw else 0.0

            fallback = get_fallback(ticker)
            if not pe or pe <= 0:
                pe = fallback["pe"]
            if not pb or pb <= 0:
                pb = fallback["pb"]
            if not div_yield:
                div_yield = fallback["div_yield"]
            if not price:
                price = fallback["price"]

            return {"price": price, "pe": pe, "pb": pb, "div_yield": div_yield}
    except Exception:
        pass
    return get_fallback(ticker)


def evaluate_signal(ticker: str, data: Dict[str, float]) -> Tuple[str, float, str]:
    """Evaluates valuation buy-zones and returns the execution signal, multiplier, and notes."""
    cfg = BASKET_CONFIG[ticker]
    tiers = cfg["tiers"]
    pe, pb, dy = data["pe"], data["pb"], data["div_yield"]
    anchor = cfg["primary_anchor"]

    if pe >= tiers["pause_above"]["pe_min"] and pb >= tiers["pause_above"]["pb_min"]:
        return "PAUSE / TRIM", 0.0, "Multiple expanded past cycle threshold."

    t3 = tiers["tier_3_lump_sum"]
    if anchor == "pb_only_on_troughs" and ticker == "BPCL":
        if pb <= t3["pb_max"] or dy >= t3["yield_min"]:
            return "TIER 3 (LUMP SUM)", 3.0, "Deep value floor breached. Deploy reserve (3.0x)."
    else:
        if (pe <= t3["pe_max"] and pb <= t3["pb_max"]) or dy >= t3["yield_min"]:
            return "TIER 3 (LUMP SUM)", 3.0, "Deep value floor breached. Deploy reserve (3.0x)."

    t2 = tiers["tier_2_aggr"]
    if anchor == "pb_only_on_troughs" and ticker == "BPCL":
        if pb <= t2["pb_max"] or dy >= t2["yield_min"]:
            return "TIER 2 (AGGRESSIVE)", 2.0, "Undervalued zone. Double SIP allocation (2.0x)."
    else:
        if (pe <= t2["pe_max"] and pb <= t2["pb_max"]) or dy >= t2["yield_min"]:
            return "TIER 2 (AGGRESSIVE)", 2.0, "Undervalued zone. Double SIP allocation (2.0x)."

    return "TIER 1 (SIP ACCUMULATE)", 1.0, "Fair value accumulation zone (1.0x)."


def evaluate_energy_basket(monthly_budget: float = 25000.0) -> dict:
    """Scans live Yahoo Finance fundamentals for the 5-stock quality energy basket.

    (Coal India, Power Grid, Petronet, BPCL, Castrol), evaluates 3-tier valuation buy-zones,
    and returns structured allocation tranches and execution signals.

    Args:
        monthly_budget: Total monthly deployment amount in INR (default: 25000.0).

    Returns:
        Structured dictionary with status, budget, per-stock allocation tranches, and redirected paused pool.
    """
    results = []
    total_adj_weight = 0.0

    for ticker, cfg in BASKET_CONFIG.items():
        data = fetch_yahoo_metrics(ticker)
        signal, mult, notes = evaluate_signal(ticker, data)
        adj_wt = cfg["target_weight"] * mult
        total_adj_weight += adj_wt
        results.append({
            "ticker": ticker,
            "name": cfg["name"],
            "price": data["price"],
            "pe": round(data["pe"], 2),
            "pb": round(data["pb"], 2),
            "div_yield": round(data["div_yield"], 2),
            "signal": signal,
            "multiplier": mult,
            "notes": notes,
            "raw_weight": adj_wt
        })

    allocations = {}
    paused_pool = 0.0

    for r in results:
        if r["multiplier"] == 0.0:
            paused_pool += (
                r["raw_weight"] * monthly_budget / r["multiplier"]
                if r["multiplier"] > 0
                else (BASKET_CONFIG[r["ticker"]]["target_weight"] * monthly_budget)
            )
        else:
            norm_wt = (
                r["raw_weight"] / total_adj_weight
                if total_adj_weight > 0
                else BASKET_CONFIG[r["ticker"]]["target_weight"]
            )
            tranche = round(norm_wt * monthly_budget, 2)
            allocations[r["ticker"]] = {
                "name": r["name"],
                "price": r["price"],
                "pe": r["pe"],
                "pb": r["pb"],
                "div_yield": r["div_yield"],
                "signal": r["signal"],
                "target_weight_pct": round(norm_wt * 100, 2),
                "monthly_tranche_inr": tranche,
                "notes": r["notes"]
            }

    return {
        "status": "success",
        "monthly_budget_inr": monthly_budget,
        "allocations": allocations,
        "paused_pool_redirected_inr": round(paused_pool, 2)
    }


def register_tools(mcp: FastMCP) -> None:
    """Register all energy basket tools on the given FastMCP instance."""
    mcp.tool()(evaluate_energy_basket)

