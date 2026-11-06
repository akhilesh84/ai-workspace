#!/usr/bin/env python3
"""
decompose_portfolio.py (v3)
Comprehensive look-through decomposition engine for Zerodha Kite portfolios.

Features:
1. Decomposes equity index ETFs (NV20, NIFTYIETF, BANKBEES, etc.) into underlying stocks.
2. Supports --mf-file to parse Mutual Fund holdings (get_mf_holdings).
3. Excludes Liquid and Arbitrage funds from equity look-through (preserves cash reserves).
4. Automated dynamic synchronization of Mutual Fund constituents (update_mf_holdings.py).
5. Generates unified multi-layer look-through analysis across Direct Demat + ETFs + MFs.
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Import dynamic sync engines from sibling scripts
try:
    from update_constituents import refresh_live_indices
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from update_constituents import refresh_live_indices

try:
    from update_mf_holdings import sync_mutual_fund_holdings
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from update_mf_holdings import sync_mutual_fund_holdings


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
                with open(ref_path, "w", encoding="utf-8") as f:
                    json.dump(kb, f, indent=2)
            else:
                provenance["status"] = "Live exchange feed (verified up-to-date)"
        except Exception as e:
            provenance["status"] = f"Cached baseline (Live sync fallback: {e})"

    return kb, provenance


def load_mf_knowledge_base(mf_holdings_data=None, live_sync: bool = True, force_sync: bool = False):
    base_dir = Path(__file__).resolve().parent.parent
    mf_ref_path = base_dir / "references" / "mf_portfolio_holdings.json"

    mf_provenance = {
        "status": "Cached baseline",
        "last_synced": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "updated_funds": [],
        "total_funds": 0
    }

    if live_sync and mf_holdings_data:
        try:
            sync_res = sync_mutual_fund_holdings(
                mf_holdings_data=mf_holdings_data,
                ref_path=mf_ref_path,
                force=force_sync
            )
            mf_provenance["status"] = sync_res.get("status", "Verified up-to-date")
            mf_provenance["last_synced"] = sync_res.get("last_synced", mf_provenance["last_synced"])
            mf_provenance["updated_funds"] = sync_res.get("updated_funds", [])
            mf_provenance["total_funds"] = sync_res.get("total_funds", 0)
        except Exception as e:
            mf_provenance["status"] = f"Cached baseline (Dynamic sync fallback: {e})"

    if mf_ref_path.exists():
        with open(mf_ref_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            funds_dict = data.get("funds", data)
            meta_dict = data.get("_meta", {})
            return funds_dict, mf_provenance, meta_dict
    return {}, mf_provenance, {}


def decompose_demat(holdings_data, kb, provenance):
    commodity_etfs = set(kb.get("commodity_etfs", []))
    equity_indices = kb.get("equity_indices", {})
    sector_map = kb.get("sector_map", {})

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

    sector_values = defaultdict(float)
    for sym, data in consolidated.items():
        sec = sector_map.get(sym, "Diversified & Others")
        sector_values[sec] += data["total_val"]

    for sym, data in commodity_holdings.items():
        sector_values["Commodities (Gold/Silver ETF)"] += data["cur_val"]

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
            "cur_val": d["cur_val"],
            "treatment": "Preserved as-is (physical commodity)"
        })

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


def analyze_mutual_funds(mf_data, mf_kb, mf_provenance=None):
    schemes = []
    total_invested = 0.0
    total_current = 0.0
    total_pnl = 0.0

    liquid_debt_funds = []
    equity_hybrid_funds = []

    for item in mf_data:
        fund_name = item.get("fund", "")
        isin = item.get("tradingsymbol", "")
        folio = item.get("folio", "")
        qty = item.get("quantity", 0.0)
        avg_nav = item.get("average_price", 0.0)
        cur_nav = item.get("last_price", 0.0)

        inv_val = qty * avg_nav
        cur_val = qty * cur_nav
        pnl = cur_val - inv_val
        ret_pct = (pnl / inv_val * 100.0) if inv_val > 0 else 0.0

        total_invested += inv_val
        total_current += cur_val
        total_pnl += pnl

        mf_meta = mf_kb.get(isin, {})
        cat = mf_meta.get("category", "Other")
        exclude = mf_meta.get("exclude_from_equity_lookthrough", False)
        if "LIQUID" in fund_name.upper() or "OVERNIGHT" in fund_name.upper() or "ARBITRAGE" in fund_name.upper():
            exclude = True
            cat = "Debt: Liquid / Cash Management"

        scheme_info = {
            "fund_name": fund_name,
            "isin": isin,
            "folio": folio,
            "qty": qty,
            "avg_nav": avg_nav,
            "cur_nav": cur_nav,
            "inv_val": inv_val,
            "cur_val": cur_val,
            "pnl": pnl,
            "ret_pct": ret_pct,
            "category": cat,
            "exclude_from_equity_lookthrough": exclude,
            "equity_alloc_pct": mf_meta.get("equity_allocation_pct", 100.0 if not exclude else 0.0),
            "as_of_disclosure_month": mf_meta.get("as_of_disclosure_month", "Latest Factsheet"),
            "constituents": mf_meta.get("constituents", [])
        }
        schemes.append(scheme_info)

        if exclude:
            liquid_debt_funds.append(scheme_info)
        else:
            equity_hybrid_funds.append(scheme_info)

    schemes.sort(key=lambda x: x["cur_val"], reverse=True)

    return {
        "schemes": schemes,
        "total_invested": total_invested,
        "total_current": total_current,
        "total_pnl": total_pnl,
        "return_pct": (total_pnl / total_invested * 100.0) if total_invested > 0 else 0.0,
        "liquid_debt_funds": liquid_debt_funds,
        "equity_hybrid_funds": equity_hybrid_funds,
        "provenance": mf_provenance or {}
    }


def compute_unified_equity_lookthrough(demat_res, mf_res, kb):
    sector_map = dict(kb.get("sector_map", {}))

    master = defaultdict(lambda: {"direct_val": 0.0, "etf_val": 0.0, "mf_val": 0.0, "total_val": 0.0, "sector": "Diversified & Others"})

    # Layer 1: Direct Demat stocks
    for sym, d in demat_res["direct_holdings"].items():
        master[sym]["direct_val"] += d["cur_val"]
        master[sym]["total_val"] += d["cur_val"]
        master[sym]["sector"] = sector_map.get(sym, "Diversified & Others")

    # Layer 2: Decomposed ETFs
    for sym, data in demat_res["consolidated"].items():
        etf_sum = sum(data["etf_vals"].values())
        if etf_sum > 0:
            master[sym]["etf_val"] += etf_sum
            master[sym]["total_val"] += etf_sum
            master[sym]["sector"] = sector_map.get(sym, "Diversified & Others")

    # Layer 3: Active Equity Mutual Funds
    mf_equity_deployed = 0.0
    for sch in mf_res["equity_hybrid_funds"]:
        cur_val = sch["cur_val"]
        eq_pct = sch["equity_alloc_pct"] / 100.0
        actual_eq_val = cur_val * eq_pct
        mf_equity_deployed += actual_eq_val

        constituents = sch.get("constituents", [])
        if constituents:
            for c in constituents:
                stk_sym = c["symbol"]
                stk_sec = c.get("sector", "Diversified")
                stk_w = c["weight"] / 100.0
                stk_val = cur_val * stk_w
                master[stk_sym]["mf_val"] += stk_val
                master[stk_sym]["total_val"] += stk_val
                if stk_sym not in sector_map and stk_sec:
                    sector_map[stk_sym] = stk_sec
                master[stk_sym]["sector"] = sector_map.get(stk_sym, stk_sec)
        else:
            gen_sym = sch["fund_name"]
            master[gen_sym]["mf_val"] += actual_eq_val
            master[gen_sym]["total_val"] += actual_eq_val
            master[gen_sym]["sector"] = "Active Equity Mutual Fund"

    demat_equity_total = (
        sum(d["cur_val"] for d in demat_res["direct_holdings"].values()) +
        sum(d["cur_val"] for d in demat_res["decomposed_etfs"].values())
    )
    total_working_equity = demat_equity_total + mf_equity_deployed

    unified_sectors = defaultdict(float)
    for sym, d in master.items():
        sec = d["sector"]
        unified_sectors[sec] += d["total_val"]

    return {
        "master_stocks": master,
        "total_working_equity": total_working_equity,
        "demat_equity_total": demat_equity_total,
        "mf_equity_deployed": mf_equity_deployed,
        "unified_sectors": unified_sectors
    }


def print_markdown_report_v3(demat_res, mf_res=None, unified_res=None):
    total_demat_val = demat_res["total_portfolio_value"]
    decomposed_etfs = demat_res["decomposed_etfs"]
    commodity_holdings = demat_res["commodity_holdings"]
    consolidated = demat_res["consolidated"]
    sector_values = demat_res["sector_values"]
    etf_prov = demat_res.get("provenance", {})
    etf_legends = demat_res.get("etf_legends", [])

    print("# 📊 Demat & ETF Consolidated Look-Through Analysis (Direct Demat + Equity ETFs)\n")
    print(f"*Explicitly includes direct Demat stock holdings and decomposed equity ETF positions.*")
    print(f"- **Total Demat Portfolio Value:** ₹{total_demat_val:,.2f}")
    if decomposed_etfs:
        etf_str = ", ".join([f"**{sym}** (₹{d['cur_val']:,.2f})" for sym, d in decomposed_etfs.items()])
        print(f"- **Decomposed Equity ETFs:** {etf_str}")
    if commodity_holdings:
        comm_str = ", ".join([f"**{sym}** (₹{d['cur_val']:,.2f})" for sym, d in commodity_holdings.items()])
        print(f"- **Preserved Commodity ETFs (As-Is):** {comm_str}")
    print(f"- **ETF Benchmark Weights Provenance:** 🟢 {etf_prov.get('status', 'Verified')} ({etf_prov.get('timestamp', '')})")
    print("\n---\n")

    print("### 🏛️ Demat & ETF True Look-Through Sector Allocation\n")
    print("| Sector | Effective Value (₹) | Portfolio Weight (%) |")
    print("|---|---|---|")
    for sec, val in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        pct = (val / total_demat_val) * 100 if total_demat_val > 0 else 0
        print(f"| **{sec}** | ₹{val:,.2f} | {pct:.2f}% |")
    print("\n---\n")

    print("### 📈 Demat & ETF Consolidated Stock Holdings (Look-Through)\n")
    etf_symbols = list(decomposed_etfs.keys())
    header = "| Rank | Stock | Direct Demat (₹) | " + " | ".join([f"Via {s} (₹)" for s in etf_symbols]) + " | Total Effective Value (₹) | Weight (%) |"
    sep = "|:---:|---|---:|" + "|".join(["---:" for _ in etf_symbols]) + "|---:|---:|"
    print(header)
    print(sep)

    sorted_stocks = sorted(consolidated.items(), key=lambda x: x[1]["total_val"], reverse=True)
    rank = 1
    minor_val = 0.0

    for sym, data in sorted_stocks:
        tot = data["total_val"]
        pct = (tot / total_demat_val) * 100 if total_demat_val > 0 else 0
        if pct < 0.5:
            minor_val += tot
            continue

        direct_str = f"₹{data['direct_val']:,.2f}"
        etf_strs = [f"₹{data['etf_vals'].get(s, 0.0):,.2f}" for s in etf_symbols]
        print(f"| {rank} | **{sym}** | {direct_str} | {' | '.join(etf_strs)} | ₹{tot:,.2f} | {pct:.2f}% |")
        rank += 1

    if minor_val > 0:
        pct_minor = (minor_val / total_demat_val) * 100
        etf_minor_strs = ["-" for _ in etf_symbols]
        print(f"| {rank} | *Remaining Demat constituents (<0.5% each)* | - | {' | '.join(etf_minor_strs)} | ₹{minor_val:,.2f} | {pct_minor:.2f}% |")

    if commodity_holdings:
        print("\n### 🪙 Commodity Holdings (Preserved As-Is)\n")
        print("| Commodity Asset | Qty | Avg Price (₹) | LTP (₹) | Current Value (₹) | Unrealized P&L (₹) |")
        print("|---|---|---|---|---|---|")
        for sym, d in commodity_holdings.items():
            print(f"| **{sym}** | {d['qty']:,} | ₹{d['avg']:,.2f} | ₹{d['ltp']:,.2f} | ₹{d['cur_val']:,.2f} | {d['pnl']:+,.2f} |")

    if etf_legends:
        print("\n### 📖 ETF to Benchmark Index Mapping (Legends)\n")
        print("| ETF Ticker | Scheme / Fund Name | Benchmark Index / Tracked Asset | Category | Portfolio Value (₹) | Look-Through Treatment |")
        print("|:---:|---|---|---|---:|---|")
        for leg in etf_legends:
            print(f"| **{leg['symbol']}** | {leg['fund_name']} | {leg['tracked_index']} | {leg['category']} | ₹{leg['cur_val']:,.2f} | {leg['treatment']} |")

    if mf_res:
        mf_prov = mf_res.get("provenance", {})
        print("\n\n---\n")
        print("# 📑 Mutual Funds Portfolio\n")
        print(f"- **Total MF Invested Value:** ₹{mf_res['total_invested']:,.2f}")
        print(f"- **Total MF Current Valuation:** ₹{mf_res['total_current']:,.2f}")
        print(f"- **Total MF Unrealized Profit:** +₹{mf_res['total_pnl']:,.2f} ({mf_res['return_pct']:+.2f}%)")
        print(f"- **MF Constituents Synchronization:** 🟢 {mf_prov.get('status', 'Verified')} ({mf_prov.get('last_synced', '')})")
        print("\n### 📋 Mutual Fund Scheme Holdings\n")
        print("| Scheme Name | Folio | Units | Avg NAV (₹) | Current NAV (₹) | Invested (₹) | Current Value (₹) | P&L (₹) | Return (%) | Weight (%) |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for s in mf_res["schemes"]:
            w_pct = (s["cur_val"] / mf_res["total_current"] * 100.0) if mf_res["total_current"] > 0 else 0
            print(f"| **{s['fund_name']}** | `{s['folio']}` | {s['qty']:,.3f} | ₹{s['avg_nav']:,.2f} | ₹{s['cur_nav']:,.2f} | ₹{s['inv_val']:,.2f} | ₹{s['cur_val']:,.2f} | {s['pnl']:+,.2f} | {s['ret_pct']:+.2f}% | {w_pct:.2f}% |")

        print("\n### 🏛️ Mutual Fund Asset Class Categorization\n")
        eq_cur = sum(s["cur_val"] for s in mf_res["equity_hybrid_funds"])
        liq_cur = sum(s["cur_val"] for s in mf_res["liquid_debt_funds"])
        print(f"- **Equity & Hybrid Schemes:** ₹{eq_cur:,.2f} ({(eq_cur/mf_res['total_current']*100):.2f}%)")
        print(f"- **Liquid & Cash Management Funds (Excluded from Equity Look-Through):** ₹{liq_cur:,.2f} ({(liq_cur/mf_res['total_current']*100):.2f}%)")

    if unified_res:
        print("\n\n---\n")
        print("# 🌐 Unified Multi-Layer Equity Look-Through Analysis (Demat + ETFs + Mutual Funds)\n")
        print(f"> *Excluding Liquid and Arbitrage funds (tracked as cash/liquidity buffer).*")
        print(f"- **Total Combined Working Equity Capital:** ₹{unified_res['total_working_equity']:,.2f}")
        print(f"  - Demat Direct Equities & ETFs: ₹{unified_res['demat_equity_total']:,.2f} ({(unified_res['demat_equity_total']/unified_res['total_working_equity']*100):.2f}%)")
        print(f"  - Active Mutual Fund Equity Sleeve: ₹{unified_res['mf_equity_deployed']:,.2f} ({(unified_res['mf_equity_deployed']/unified_res['total_working_equity']*100):.2f}%)")
        print("\n### 📈 Consolidated Single-Stock Exposures (Combined)\n")
        print("| Rank | Stock Symbol | Direct Demat (₹) | Via ETFs (₹) | Via Mutual Funds (₹) | Total Combined Value (₹) | Share of Total Equity (%) |")
        print("|:---:|---|---:|---:|---:|---:|---:|")

        tot_eq = unified_res["total_working_equity"]
        sorted_m = sorted(unified_res["master_stocks"].items(), key=lambda x: x[1]["total_val"], reverse=True)
        r = 1
        tail_val = 0.0
        for sym, d in sorted_m:
            pct = (d["total_val"] / tot_eq * 100) if tot_eq > 0 else 0
            if pct < 0.5 or "OTHER" in sym.upper():
                tail_val += d["total_val"]
                continue
            print(f"| {r} | **{sym}** | ₹{d['direct_val']:,.2f} | ₹{d['etf_val']:,.2f} | ₹{d['mf_val']:,.2f} | **₹{d['total_val']:,.2f}** | **{pct:.2f}%** |")
            r += 1

        if tail_val > 0:
            print(f"| {r} | *Long Tail / Other Constituents (<0.5% each)* | - | - | - | **₹{tail_val:,.2f}** | **{(tail_val/tot_eq*100):.2f}%** |")

        print("\n### 🏛️ Unified Look-Through Sector Allocation (All Equity)\n")
        print("| Sector | Combined Value (₹) | Share of Total Equity (%) |")
        print("|---|---|---|")
        for sec, val in sorted(unified_res["unified_sectors"].items(), key=lambda x: x[1], reverse=True):
            print(f"| **{sec}** | ₹{val:,.2f} | {(val/tot_eq*100):.2f}% |")


def main():
    parser = argparse.ArgumentParser(description="Decompose ETFs and Mutual Funds in Kite holdings into look-through equity exposure (v3).")
    parser.add_argument("file", nargs="?", help="Path to JSON file containing Kite stock/ETF holdings. If omitted, reads stdin.")
    parser.add_argument("--mf-file", help="Path to JSON file containing Mutual Fund holdings from get_mf_holdings.")
    parser.add_argument("--skip-live-sync", action="store_true", help="Skip querying live exchange feeds for ETF constituent updates.")
    parser.add_argument("--skip-mf-sync", action="store_true", help="Skip dynamic synchronization of Mutual Fund constituents.")
    parser.add_argument("--force-mf-sync", action="store_true", help="Force refresh of Mutual Fund disclosures regardless of cache.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            holdings = json.load(f)
    else:
        holdings = json.load(sys.stdin)

    kb, provenance = load_knowledge_base(live_sync=(not args.skip_live_sync))
    demat_res = decompose_demat(holdings, kb, provenance)

    mf_res = None
    unified_res = None
    if args.mf_file:
        with open(args.mf_file, "r", encoding="utf-8") as f:
            mf_data = json.load(f)

        mf_kb, mf_provenance, mf_meta = load_mf_knowledge_base(
            mf_holdings_data=mf_data,
            live_sync=(not args.skip_mf_sync),
            force_sync=args.force_mf_sync
        )
        mf_res = analyze_mutual_funds(mf_data, mf_kb, mf_provenance=mf_provenance)
        unified_res = compute_unified_equity_lookthrough(demat_res, mf_res, kb)

    if args.json:
        out = {
            "demat_analysis": demat_res,
            "mf_analysis": mf_res,
            "unified_analysis": unified_res
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        print_markdown_report_v3(demat_res, mf_res, unified_res)


if __name__ == "__main__":
    main()
