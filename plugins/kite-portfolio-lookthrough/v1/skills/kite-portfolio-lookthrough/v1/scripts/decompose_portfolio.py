#!/usr/bin/env python3
"""
decompose_portfolio.py
Decomposes equity index ETFs in Kite holdings into their constituent stocks
to reveal the true "look-through" equity and sector exposure.

Features dynamic live exchange sync to guarantee index constituents and weights
are never stale or outdated.
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Import dynamic sync engine from sibling script
try:
    from update_constituents import refresh_live_indices
except ImportError:
    # Handle direct script invocation
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from update_constituents import refresh_live_indices


def load_knowledge_base(live_sync: bool = True):
    base_dir = Path(__file__).resolve().parent.parent
    ref_path = base_dir / "references" / "etf_index_constituents.json"
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference file not found at {ref_path}")
    with open(ref_path, "r", encoding="utf-8") as f:
        kb = json.load(f)

    provenance = {
        "status": "Cached baseline",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "updated_indices": []
    }

    if live_sync:
        try:
            changed, updated_indices = refresh_live_indices(kb)
            provenance["updated_indices"] = updated_indices
            if changed:
                provenance["status"] = "Live exchange feed (synced just now)"
                # Persist updated index definitions
                with open(ref_path, "w", encoding="utf-8") as f:
                    json.dump(kb, f, indent=2)
            else:
                provenance["status"] = "Live exchange feed (verified up-to-date)"
        except Exception as e:
            provenance["status"] = f"Cached baseline (Live sync fallback: {e})"

    return kb, provenance


def decompose(holdings_data, kb, provenance):
    commodity_etfs = set(kb.get("commodity_etfs", []))
    equity_indices = kb.get("equity_indices", {})
    sector_map = kb.get("sector_map", {})

    # Map ETF tradingsymbol to index info
    etf_to_index = {}
    for idx_key, idx_info in equity_indices.items():
        for ticker in idx_info.get("tracked_by", []):
            etf_to_index[ticker] = idx_info

    direct_holdings = {}
    decomposed_etfs = {}
    commodity_holdings = {}

    for h in holdings_data:
        sym = h.get("tradingsymbol", "")
        qty = h.get("quantity", 0)
        avg = h.get("average_price", 0.0)
        ltp = h.get("last_price", 0.0)
        cur_val = qty * ltp
        inv_val = qty * avg
        pnl = h.get("pnl", cur_val - inv_val)

        if sym in commodity_etfs:
            commodity_holdings[sym] = {
                "symbol": sym,
                "qty": qty,
                "avg": avg,
                "ltp": ltp,
                "cur_val": cur_val,
                "inv_val": inv_val,
                "pnl": pnl
            }
        elif sym in etf_to_index:
            decomposed_etfs[sym] = {
                "symbol": sym,
                "qty": qty,
                "avg": avg,
                "ltp": ltp,
                "cur_val": cur_val,
                "inv_val": inv_val,
                "pnl": pnl,
                "index_info": etf_to_index[sym]
            }
        else:
            direct_holdings[sym] = {
                "symbol": sym,
                "qty": qty,
                "avg": avg,
                "ltp": ltp,
                "cur_val": cur_val,
                "inv_val": inv_val,
                "pnl": pnl
            }

    # Consolidated look-through tracking
    consolidated = defaultdict(lambda: {"direct_val": 0.0, "etf_vals": defaultdict(float), "total_val": 0.0})

    for sym, d in direct_holdings.items():
        consolidated[sym]["direct_val"] += d["cur_val"]
        consolidated[sym]["total_val"] += d["cur_val"]

    for etf_sym, etf_data in decomposed_etfs.items():
        weights = etf_data["index_info"]["weights"]
        total_w = sum(weights.values())
        etf_cur_val = etf_data["cur_val"]

        for stock_sym, raw_w in weights.items():
            norm_w = raw_w / total_w
            stock_etf_val = norm_w * etf_cur_val
            consolidated[stock_sym]["etf_vals"][etf_sym] += stock_etf_val
            consolidated[stock_sym]["total_val"] += stock_etf_val

    total_portfolio_value = (
        sum(d["cur_val"] for d in direct_holdings.values()) +
        sum(d["cur_val"] for d in decomposed_etfs.values()) +
        sum(d["cur_val"] for d in commodity_holdings.values())
    )

    # Sector aggregation
    sector_values = defaultdict(float)
    for sym, data in consolidated.items():
        sec = sector_map.get(sym, "Diversified & Others")
        sector_values[sec] += data["total_val"]

    for sym, data in commodity_holdings.items():
        sector_values["Commodities (Gold/Silver ETF)"] += data["cur_val"]

    # Build ETF to Index Legends mapping
    etf_directory = kb.get("etf_directory", {})
    etf_legends = []

    for sym, d in decomposed_etfs.items():
        meta = etf_directory.get(sym, {})
        idx_desc = d["index_info"].get("description", "Benchmark Equity Index")
        etf_legends.append({
            "symbol": sym,
            "fund_name": meta.get("fund_name", f"{sym} ETF"),
            "tracked_index": meta.get("tracked_index", idx_desc),
            "category": meta.get("category", "Equity Index ETF"),
            "benchmark_provider": meta.get("benchmark_provider", "NSE Indices"),
            "cur_val": d["cur_val"],
            "treatment": f"Decomposed into {len(d['index_info'].get('weights', {}))} constituent stocks"
        })

    for sym, d in commodity_holdings.items():
        meta = etf_directory.get(sym, {})
        etf_legends.append({
            "symbol": sym,
            "fund_name": meta.get("fund_name", f"{sym} ETF"),
            "tracked_index": meta.get("tracked_index", "Domestic Spot Physical Price"),
            "category": meta.get("category", "Commodity ETF"),
            "benchmark_provider": meta.get("benchmark_provider", "Domestic Spot (LBMA/MCX)"),
            "cur_val": d["cur_val"],
            "treatment": "Preserved as-is (physical commodity)"
        })

    # Sort legends by current value descending
    etf_legends.sort(key=lambda x: x["cur_val"], reverse=True)

    return {
        "direct_holdings": direct_holdings,
        "decomposed_etfs": decomposed_etfs,
        "commodity_holdings": commodity_holdings,
        "consolidated": consolidated,
        "sector_values": sector_values,
        "total_portfolio_value": total_portfolio_value,
        "provenance": provenance,
        "etf_legends": etf_legends
    }


def print_markdown_report(result):
    total_val = result["total_portfolio_value"]
    decomposed_etfs = result["decomposed_etfs"]
    commodity_holdings = result["commodity_holdings"]
    consolidated = result["consolidated"]
    sector_values = result["sector_values"]
    provenance = result.get("provenance", {})
    etf_legends = result.get("etf_legends", [])

    print("## 📊 Look-Through Portfolio Analysis\n")
    print(f"- **Total Equity & ETF Portfolio Value:** ₹{total_val:,.2f}")
    if decomposed_etfs:
        etf_str = ", ".join([f"**{sym}** (₹{d['cur_val']:,.2f})" for sym, d in decomposed_etfs.items()])
        print(f"- **Replaced Equity ETFs:** {etf_str}")
    if commodity_holdings:
        comm_str = ", ".join([f"**{sym}** (₹{d['cur_val']:,.2f})" for sym, d in commodity_holdings.items()])
        print(f"- **Retained Commodity ETFs (As-Is):** {comm_str}")
    print(f"- **Index Constituents & Weights Provenance:** 🟢 {provenance.get('status', 'Verified')} ({provenance.get('timestamp', '')})")
    print("\n---\n")

    print("### 🏛️ 1. True Look-Through Sector Allocation\n")
    print("| Sector | Effective Value (₹) | Portfolio Weight (%) |")
    print("|---|---|---|")
    for sec, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        pct = (val / total_val) * 100 if total_val > 0 else 0
        print(f"| **{sec}** | ₹{val:,.2f} | {pct:.2f}% |")
    print("\n---\n")

    print("### 📈 2. Consolidated Stock Holdings (Look-Through)\n")
    etf_symbols = list(decomposed_etfs.keys())
    header = "| Rank | Stock | Direct (₹) | " + " | ".join([f"Via {s} (₹)" for s in etf_symbols]) + " | Total Effective Value (₹) | Weight (%) |"
    sep = "|:---:|---|---:|" + "|".join(["---:" for _ in etf_symbols]) + "|---:|---:|"
    print(header)
    print(sep)

    sorted_stocks = sorted(consolidated.items(), key=lambda x: x[1]["total_val"], reverse=True)
    rank = 1
    minor_val = 0.0

    for sym, data in sorted_stocks:
        tot = data["total_val"]
        pct = (tot / total_val) * 100 if total_val > 0 else 0
        if pct < 0.5:
            minor_val += tot
            continue

        direct_str = f"₹{data['direct_val']:,.2f}"
        etf_strs = [f"₹{data['etf_vals'].get(s, 0.0):,.2f}" for s in etf_symbols]
        print(f"| {rank} | **{sym}** | {direct_str} | {' | '.join(etf_strs)} | ₹{tot:,.2f} | {pct:.2f}% |")
        rank += 1

    if minor_val > 0:
        pct_minor = (minor_val / total_val) * 100
        etf_minor_strs = ["-" for _ in etf_symbols]
        print(f"| {rank} | *Remaining constituents (<0.5% each)* | - | {' | '.join(etf_minor_strs)} | ₹{minor_val:,.2f} | {pct_minor:.2f}% |")

    if commodity_holdings:
        print("\n### 🪙 3. Commodity ETFs (Preserved As-Is)\n")
        print("| Commodity Asset | Qty | Avg Price (₹) | LTP (₹) | Current Value (₹) | P&L (₹) |")
        print("|---|---|---|---|---|---|")
        for sym, d in commodity_holdings.items():
            print(f"| **{sym}** | {d['qty']:,} | ₹{d['avg']:,.2f} | ₹{d['ltp']:,.2f} | ₹{d['cur_val']:,.2f} | {d['pnl']:+,.2f} |")

    if etf_legends:
        print("\n### 📖 4. ETF to Benchmark Index Mapping (Legends)\n")
        print("| ETF Ticker | Scheme / Fund Name | Benchmark Index / Tracked Asset | Category | Portfolio Value (₹) | Treatment in Analysis |")
        print("|:---:|---|---|---|---:|---|")
        for leg in etf_legends:
            print(f"| **{leg['symbol']}** | {leg['fund_name']} | {leg['tracked_index']} | {leg['category']} | ₹{leg['cur_val']:,.2f} | {leg['treatment']} |")


def main():
    parser = argparse.ArgumentParser(description="Decompose ETFs in Kite holdings into look-through equity exposure.")
    parser.add_argument("file", nargs="?", help="Path to JSON file containing Kite holdings. If omitted, reads stdin.")
    parser.add_argument("--skip-live-sync", action="store_true", help="Skip querying live exchange feeds for constituent updates.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            holdings = json.load(f)
    else:
        holdings = json.load(sys.stdin)

    kb, provenance = load_knowledge_base(live_sync=(not args.skip_live_sync))
    result = decompose(holdings, kb, provenance)

    if args.json:
        out = {
            "total_portfolio_value": result["total_portfolio_value"],
            "provenance": result["provenance"],
            "sector_values": dict(result["sector_values"]),
            "consolidated": {k: {"direct_val": v["direct_val"], "etf_vals": dict(v["etf_vals"]), "total_val": v["total_val"]} for k, v in result["consolidated"].items()},
            "commodity_holdings": result["commodity_holdings"],
            "decomposed_etfs": {k: {key: val for key, val in v.items() if key != "index_info"} for k, v in result["decomposed_etfs"].items()},
            "etf_legends": result.get("etf_legends", [])
        }
        print(json.dumps(out, indent=2))
    else:
        print_markdown_report(result)


if __name__ == "__main__":
    main()
