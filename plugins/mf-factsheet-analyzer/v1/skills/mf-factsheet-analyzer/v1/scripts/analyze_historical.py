#!/usr/bin/env python3
"""
analyze_historical.py - 36-Month Mutual Fund Historical Analytics Engine
Analyzes:
  1. Capital Utilization Patterns (Asset mix progression)
  2. Dry Powder & Cash Reserves Dynamics (Timeline, median, peak, deployment velocity)
  3. Investment Rotation & Portfolio Turnover (PTR trajectory, core anchors vs churn)
  4. Sector Allocation Drift (1M, 3M, 6M, 12M, 36M net changes)
  5. Concentration Risk (Sector HHI, Top N stocks, SEBI 10% ceiling audit)
  6. Performance & NAV Drawdown Correlation
"""

import sys
import os
import json
import math
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from fetch_factsheet import acquire_factsheet_data


def calculate_nav_metrics(nav_series: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Computes 36-month total return, CAGR, and max drawdown from daily NAV records.
    NAV records are sorted newest to oldest: [{'date': '05-11-2026', 'nav': '92.7055'}, ...]
    """
    if not nav_series or len(nav_series) < 2:
        return {}

    try:
        latest_nav = float(nav_series[0]["nav"])
        oldest_nav = float(nav_series[-1]["nav"])
        latest_date = nav_series[0]["date"]
        oldest_date = nav_series[-1]["date"]

        total_return_pct = round(((latest_nav / oldest_nav) - 1.0) * 100.0, 2)
        
        # Approximate years
        trading_days = len(nav_series)
        years = max(0.5, round(trading_days / 250.0, 2))
        cagr_pct = round((((latest_nav / oldest_nav) ** (1.0 / years)) - 1.0) * 100.0, 2)

        # Max drawdown computation
        nav_values = [float(x["nav"]) for x in reversed(nav_series)]  # oldest to newest
        peak = nav_values[0]
        max_drawdown = 0.0

        for val in nav_values:
            if val > peak:
                peak = val
            dd = (val - peak) / peak
            if dd < max_drawdown:
                max_drawdown = dd

        max_dd_pct = round(max_drawdown * 100.0, 2)

        return {
            "period_start_date": oldest_date,
            "period_end_date": latest_date,
            "trading_days_analyzed": trading_days,
            "start_nav": oldest_nav,
            "end_nav": latest_nav,
            "total_return_pct": total_return_pct,
            "cagr_3y_pct": cagr_pct,
            "max_drawdown_pct": max_dd_pct
        }
    except Exception as e:
        print(f"⚠️ Error computing NAV metrics: {e}", file=sys.stderr)
        return {}


def analyze_portfolio_history(factsheet_data: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = factsheet_data.get("monthly_snapshots", [])
    if not snapshots:
        return {"error": "No monthly snapshots available to analyze."}

    # Ensure chronological order (oldest to newest for drift analysis)
    # Check if first item is older or newer
    if "month_year" in snapshots[0] and "month_year" in snapshots[-1]:
        if snapshots[0]["month_year"] > snapshots[-1]["month_year"]:
            snapshots = list(reversed(snapshots))
    elif "as_of_date" in snapshots[0]:
        # Keep as is or sort by file/date
        pass

    total_months = len(snapshots)
    latest = snapshots[-1]
    oldest = snapshots[0]

    # 1. Capital Utilization & Dry Powder Timeline
    dry_powder_timeline = []
    ptr_timeline = []
    equity_timeline = []
    regime_counts = {"DEFENSIVE_DRY_POWDER_ACCUMULATION": 0, "AGGRESSIVE_CAPITAL_DEPLOYED": 0, "NEUTRAL_BALANCED": 0}

    for snap in snapshots:
        m_label = snap.get("month_year") or snap.get("as_of_date", "N/A")
        alloc = snap.get("asset_allocation", {})
        dp = alloc.get("dry_powder_total_pct", alloc.get("treps_reverse_repo_pct", 0.0))
        eq = alloc.get("domestic_equity_pct", 0.0) + alloc.get("foreign_equity_pct", 0.0)
        ptr = snap.get("portfolio_turnover_ratio_ex_arbitrage") or snap.get("portfolio_turnover_ratio_incl_arbitrage") or 0.0
        
        regime = snap.get("capital_deployment_regime")
        if not regime:
            regime = "DEFENSIVE_DRY_POWDER_ACCUMULATION" if dp >= 13.0 else ("AGGRESSIVE_CAPITAL_DEPLOYED" if dp <= 9.0 else "NEUTRAL_BALANCED")
        regime_counts[regime] = regime_counts.get(regime, 0) + 1

        dry_powder_timeline.append({"month": m_label, "dry_powder_pct": dp, "equity_pct": round(eq, 2), "regime": regime})
        ptr_timeline.append({"month": m_label, "ptr_pct": ptr})
        equity_timeline.append({"month": m_label, "equity_pct": round(eq, 2)})

    dp_values = [x["dry_powder_pct"] for x in dry_powder_timeline]
    ptr_values = [x["ptr_pct"] for x in ptr_timeline if x["ptr_pct"] > 0]

    current_dp = dp_values[-1] if dp_values else 0.0
    peak_dp = max(dp_values) if dp_values else 0.0
    min_dp = min(dp_values) if dp_values else 0.0
    median_dp = round(sorted(dp_values)[len(dp_values) // 2], 2) if dp_values else 0.0

    avg_ptr = round(sum(ptr_values) / len(ptr_values), 2) if ptr_values else 0.0
    latest_ptr = ptr_values[-1] if ptr_values else 0.0

    # 2. Deployment Velocity Events (Rapid cash deployments during market pullbacks)
    deployment_events = []
    for i in range(1, len(dry_powder_timeline)):
        prev_dp = dry_powder_timeline[i - 1]["dry_powder_pct"]
        curr_dp_val = dry_powder_timeline[i]["dry_powder_pct"]
        delta_dp = round(curr_dp_val - prev_dp, 2)
        if delta_dp <= -1.8:  # Cash dropped by >= 1.8% in a single month
            deployment_events.append({
                "month": dry_powder_timeline[i]["month"],
                "cash_reduction_pct": abs(delta_dp),
                "from_dp": prev_dp,
                "to_dp": curr_dp_val,
                "interpretation": f"Aggressive capital deployment: Fund deployed {abs(delta_dp):.2f}% dry powder into equity opportunities"
            })

    # 3. Sector Allocation Drift Analysis
    latest_sectors = latest.get("sectors") or latest.get("sector_allocation", {})
    # Historical comparisons: 1M, 3M, 6M, 12M, 36M (or oldest)
    idx_1m = max(0, total_months - 2)
    idx_3m = max(0, total_months - 4)
    idx_6m = max(0, total_months - 7)
    idx_12m = max(0, total_months - 13)
    idx_36m = max(0, total_months - 37)
    idx_oldest = 0

    sectors_1m = snapshots[idx_1m].get("sectors") or snapshots[idx_1m].get("sector_allocation", {})
    sectors_3m = snapshots[idx_3m].get("sectors") or snapshots[idx_3m].get("sector_allocation", {})
    sectors_6m = snapshots[idx_6m].get("sectors") or snapshots[idx_6m].get("sector_allocation", {})
    sectors_12m = snapshots[idx_12m].get("sectors") or snapshots[idx_12m].get("sector_allocation", {})
    sectors_36m = snapshots[idx_36m].get("sectors") or snapshots[idx_36m].get("sector_allocation", {})
    sectors_oldest = oldest.get("sectors") or oldest.get("sector_allocation", {})

    sector_drift_table = []
    for sec, curr_w in sorted(latest_sectors.items(), key=lambda x: x[1], reverse=True):
        if sec in ["Cash & Cash Equivalents", "Other / Diversified", "Other / Unclassified"]:
            continue
        w_1m = sectors_1m.get(sec, 0.0)
        w_3m = sectors_3m.get(sec, 0.0)
        w_6m = sectors_6m.get(sec, 0.0)
        w_12m = sectors_12m.get(sec, 0.0)
        w_36m = sectors_36m.get(sec, 0.0)
        w_oldest = sectors_oldest.get(sec, 0.0)

        d_1m = round(curr_w - w_1m, 2)
        d_3m = round(curr_w - w_3m, 2)
        d_6m = round(curr_w - w_6m, 2)
        d_12m = round(curr_w - w_12m, 2)
        d_36m = round(curr_w - w_36m, 2)
        d_total = round(curr_w - w_oldest, 2)

        # Trend tag
        if d_3m >= 1.0:
            trend = "ACCUMULATING"
        elif d_3m <= -1.0:
            trend = "TRIMMING"
        else:
            trend = "STABLE"

        sector_drift_table.append({
            "sector": sec,
            "current_weight_pct": curr_w,
            "delta_1m": d_1m,
            "delta_3m": d_3m,
            "delta_6m": d_6m,
            "delta_12m": d_12m,
            "delta_36m": d_36m,
            "delta_total": d_total,
            "trend": trend
        })

    # Sort sectors by current weight
    sector_drift_table = sorted(sector_drift_table, key=lambda x: x["current_weight_pct"], reverse=True)

    # 4. Concentration Risk Metrics
    conc = latest.get("concentration_risk", {})
    # If not already present in latest snapshot, calculate
    if not conc:
        sec_weights = [v for k, v in latest_sectors.items() if k != "Cash & Cash Equivalents"]
        sorted_secs = sorted(sec_weights, reverse=True)
        top_1_sec = sorted_secs[0] if sorted_secs else 0.0
        top_3_sec = round(sum(sorted_secs[:3]), 2)
        top_5_sec = round(sum(sorted_secs[:5]), 2)
        hhi = round(sum(w ** 2 for w in sorted_secs), 1)

        holdings = latest.get("top_holdings", [])
        top_1_stk = holdings[0].get("weight_pct") or holdings[0].get("weight", 0.0) if holdings else 0.0
        top_5_stk = round(sum(h.get("weight_pct") or h.get("weight", 0.0) for h in holdings[:5]), 2)
        top_10_stk = round(sum(h.get("weight_pct") or h.get("weight", 0.0) for h in holdings[:10]), 2)

        conc = {
            "top_1_stock_pct": top_1_stk,
            "top_5_stock_pct": top_5_stk,
            "top_10_stock_pct": top_10_stk,
            "top_1_sector_pct": top_1_sec,
            "top_3_sector_pct": top_3_sec,
            "top_5_sector_pct": top_5_sec,
            "sector_hhi": hhi,
            "sector_hhi_category": "CONCENTRATED" if hhi > 2500 else ("MODERATE" if hhi >= 1500 else "DIVERSIFIED"),
            "sebi_10pct_cap_breached": any((h.get("weight_pct") or h.get("weight", 0.0)) >= 10.0 for h in holdings)
        }

    # 5. Core Holding Stability vs Churn
    # Track which holdings were present in both oldest and newest snapshot
    oldest_holdings = {h.get("name") or h.get("symbol"): h.get("weight_pct") or h.get("weight", 0.0) for h in oldest.get("top_holdings", [])}
    latest_holdings = {h.get("name") or h.get("symbol"): h.get("weight_pct") or h.get("weight", 0.0) for h in latest.get("top_holdings", [])}

    core_anchors = []
    for name, curr_w in latest_holdings.items():
        if name in oldest_holdings:
            core_anchors.append({
                "name": name,
                "current_weight": curr_w,
                "oldest_weight": oldest_holdings[name],
                "status": "LONG_TERM_CORE_ANCHOR (>36M)"
            })

    # 6. NAV Performance Correlation
    nav_metrics = {}
    if "live_nav_series" in factsheet_data:
        nav_metrics = calculate_nav_metrics(factsheet_data["live_nav_series"])

    return {
        "scheme_code": factsheet_data.get("scheme_code"),
        "scheme_name": factsheet_data.get("scheme_name"),
        "fund_house": factsheet_data.get("fund_house"),
        "scheme_category": factsheet_data.get("scheme_category"),
        "benchmark": factsheet_data.get("benchmark", "Nifty 500 TRI"),
        "months_analyzed": total_months,
        "start_month": oldest.get("month_year") or oldest.get("as_of_date"),
        "end_month": latest.get("month_year") or latest.get("as_of_date"),
        "current_aum_crores": latest.get("aum_crores"),
        "dry_powder_analysis": {
            "current_dry_powder_pct": current_dp,
            "historical_peak_pct": peak_dp,
            "historical_low_pct": min_dp,
            "historical_median_pct": median_dp,
            "current_status": "HIGH_DRY_POWDER (Opportunity Ready)" if current_dp >= 12.0 else ("LOW_DRY_POWDER (Fully Deployed)" if current_dp <= 8.5 else "OPTIMAL_DRY_POWDER"),
            "deployment_events_count": len(deployment_events),
            "recent_deployment_events": deployment_events[-4:] if deployment_events else []
        },
        "capital_rotation_analysis": {
            "latest_ptr_pct": latest_ptr,
            "average_ptr_36m_pct": avg_ptr,
            "rotation_speed": "LOW_CONVICTION_BUY_AND_HOLD (<25%)" if avg_ptr < 25.0 else ("MODERATE_ROTATION (25-60%)" if avg_ptr <= 60.0 else "HIGH_CHURN (>60%)"),
            "core_anchors_36m": core_anchors
        },
        "sector_drift_analysis": {
            "top_accumulated_sector_3m": max(sector_drift_table, key=lambda x: x["delta_3m"])["sector"] if sector_drift_table else "None",
            "top_trimmed_sector_3m": min(sector_drift_table, key=lambda x: x["delta_3m"])["sector"] if sector_drift_table else "None",
            "sectors": sector_drift_table
        },
        "concentration_risk": conc,
        "nav_performance": nav_metrics,
        "dry_powder_timeline": dry_powder_timeline
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze 36-month historical factsheet metrics of a mutual fund.")
    parser.add_argument("--scheme-code", "-s", type=int, required=True, help="AMFI scheme code (e.g. 122639)")
    parser.add_argument("--local-dir", "-d", type=str, help="Directory containing monthly portfolio files")
    parser.add_argument("--json", action="store_true", help="Output analysis results strictly in JSON format")
    args = parser.parse_args()

    # 1. Acquire factsheet data
    factsheet_data = acquire_factsheet_data(args.scheme_code, local_dir=args.local_dir)
    
    # 2. Run historical analytics
    analysis = analyze_portfolio_history(factsheet_data)

    if args.json:
        print(json.dumps(analysis, indent=2))
        return

    # Formatted terminal summary
    print(f"\n=======================================================")
    print(f"📈 36-MONTH FACTSHEET ANALYSIS: {analysis.get('scheme_name')}")
    print(f"   Fund House: {analysis.get('fund_house')} | Benchmark: {analysis.get('benchmark')}")
    print(f"   Horizon: {analysis.get('start_month')} ➔ {analysis.get('end_month')} ({analysis.get('months_analyzed')} months)")
    if analysis.get("current_aum_crores"):
        print(f"   Current AUM: ₹{analysis['current_aum_crores']:,} Cr")
    print(f"-------------------------------------------------------")

    # Dry powder
    dp = analysis["dry_powder_analysis"]
    print(f"💵 DRY POWDER & CASH RESERVES:")
    print(f"   • Current Cash/TREPS Reserve : {dp['current_dry_powder_pct']}% ({dp['current_status']})")
    print(f"   • 36-Month Range             : {dp['historical_low_pct']}% (Low) ➔ {dp['historical_peak_pct']}% (Peak)")
    print(f"   • 36-Month Median            : {dp['historical_median_pct']}%")
    print(f"   • Opportunistic Deployments  : {dp['deployment_events_count']} rapid cash injection events identified")

    # Capital rotation
    rot = analysis["capital_rotation_analysis"]
    print(f"\n🔄 CAPITAL ROTATION & TURNOVER:")
    print(f"   • Latest PTR                 : {rot['latest_ptr_pct']}%")
    print(f"   • 36-Month Average PTR       : {rot['average_ptr_36m_pct']}% ({rot['rotation_speed']})")
    print(f"   • Long-Term Core Anchors     : {len(rot['core_anchors_36m'])} stocks held continuously > 36 months")
    for a in rot['core_anchors_36m'][:4]:
        print(f"     - {a['name']:25}: {a['current_weight']}% current (was {a['oldest_weight']}% 36m ago)")

    # Sector drift
    sd = analysis["sector_drift_analysis"]
    print(f"\n🏢 TOP SECTOR ALLOCATIONS & DRIFT:")
    print(f"   {'Sector':<26} {'Current':<9} {'1M Δ':<7} {'3M Δ':<7} {'12M Δ':<8} {'Trend'}")
    print(f"   {'-'*65}")
    for s in sd["sectors"][:6]:
        print(f"   {s['sector']:<26} {s['current_weight_pct']:>6.2f}%  {s['delta_1m']:>+5.2f}% {s['delta_3m']:>+5.2f}% {s['delta_12m']:>+6.2f}%   {s['trend']}")

    # Concentration risk
    cr = analysis["concentration_risk"]
    print(f"\n⚠️ CONCENTRATION RISK ASSESSMENT:")
    print(f"   • Sector Concentration HHI   : {cr.get('sector_hhi')} ({cr.get('sector_hhi_category')})")
    print(f"   • Top 3 Sectors Weight       : {cr.get('top_3_sector_pct')}%")
    print(f"   • Top 10 Stocks Weight       : {cr.get('top_10_stock_pct')}%")
    sebi_flag = "⚠️ BREACHED (>10%)" if cr.get('sebi_10pct_cap_breached') else "✅ COMPLIANT (<10% single stock cap)"
    print(f"   • SEBI Single-Stock Cap      : {sebi_flag}")

    # Performance
    perf = analysis.get("nav_performance", {})
    if perf:
        print(f"\n📊 36-MONTH NAV PERFORMANCE & RESILIENCE:")
        print(f"   • 36M Total Return           : {perf.get('total_return_pct')}%")
        print(f"   • 3-Year CAGR                : {perf.get('cagr_3y_pct')}%")
        print(f"   • Maximum Drawdown           : {perf.get('max_drawdown_pct')}%")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()

