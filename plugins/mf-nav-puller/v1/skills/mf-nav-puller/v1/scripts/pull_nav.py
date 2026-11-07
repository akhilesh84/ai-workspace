#!/usr/bin/env python3
"""
pull_nav.py - Main Mutual Fund NAV Puller & Performance Analyzer
Fetches NAV data via the Swagger/OpenAPI endpoint on mfapi.in:
  GET https://api.mfapi.in/mf/{scheme_code}?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD

Features:
  - Resolves fund names or scheme codes with typo recovery (e.g. 'HDFV midcap' -> 'HDFC Mid Cap')
  - Automatically isolates 'Direct Plan - Growth'
  - Converts natural relative horizons ('last 15 months', 'since inception', '3 years') to ISO 8601
  - Calculates Return %, CAGR %, Period High/Low, Max Drawdown %, and Volatility %
  - Supports Markdown, CSV, and interactive HTML Chart.js dashboard outputs
"""

import sys
import os
import json
import math
import urllib.request
import urllib.parse
import urllib.error
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from resolve_scheme import resolve_fund, fetch_scheme_meta
from date_parser import parse_horizon_or_dates
from render_nav_report import generate_markdown_report, export_to_csv, generate_interactive_html

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


def fetch_nav_data(
    scheme_code: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeout: int = 15
) -> Optional[Dict[str, Any]]:
    """
    Queries GET https://api.mfapi.in/mf/{scheme_code}
    Optionally appends ?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
    """
    params = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date

    query_str = urllib.parse.urlencode(params)
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    if query_str:
        url = f"{url}?{query_str}"

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Error fetching NAV data from {url}: {e}", file=sys.stderr)
        return None


def compute_performance_metrics(nav_records: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Computes performance, drawdown, and volatility metrics from NAV records.
    Records from mfapi.in are ordered newest first:
    [{'date': '06-11-2026', 'nav': '93.9483'}, ...]
    """
    if not nav_records:
        return {}

    trading_days = len(nav_records)
    newest = nav_records[0]
    oldest = nav_records[-1]

    end_nav = float(newest["nav"])
    start_nav = float(oldest["nav"])
    end_date_str = newest["date"]
    start_date_str = oldest["date"]

    # Total Return %
    total_return_pct = round(((end_nav / start_nav) - 1.0) * 100.0, 2)

    # Date duration & CAGR
    cagr_pct = None
    try:
        dt_start = datetime.strptime(start_date_str, "%d-%m-%Y")
        dt_end = datetime.strptime(end_date_str, "%d-%m-%Y")
        delta_days = (dt_end - dt_start).days
        years = delta_days / 365.25
        if years >= 0.5:
            cagr = ((end_nav / start_nav) ** (1.0 / years)) - 1.0
            cagr_pct = round(cagr * 100.0, 2)
    except Exception:
        pass

    # Sort oldest to newest for chronological traversal
    chronological = list(reversed(nav_records))
    
    # Period High & Low
    high_rec = max(chronological, key=lambda x: float(x["nav"]))
    low_rec = min(chronological, key=lambda x: float(x["nav"]))

    period_high_nav = float(high_rec["nav"])
    period_high_date = high_rec["date"]
    period_low_nav = float(low_rec["nav"])
    period_low_date = low_rec["date"]

    # Maximum Drawdown & Daily Returns for Volatility
    running_peak = float(chronological[0]["nav"])
    max_drawdown = 0.0
    daily_returns = []

    for i, item in enumerate(chronological):
        val = float(item["nav"])
        if val > running_peak:
            running_peak = val
        dd = (val - running_peak) / running_peak
        if dd < max_drawdown:
            max_drawdown = dd

        if i > 0:
            prev_val = float(chronological[i - 1]["nav"])
            if prev_val > 0 and val > 0:
                ret = math.log(val / prev_val)
                daily_returns.append(ret)

    max_drawdown_pct = round(max_drawdown * 100.0, 2)

    # Annualized Volatility
    ann_vol_pct = None
    if len(daily_returns) > 10:
        mean_ret = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        daily_std = math.sqrt(variance)
        ann_vol = daily_std * math.sqrt(250)
        ann_vol_pct = round(ann_vol * 100.0, 2)

    return {
        "trading_days": trading_days,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "start_nav": start_nav,
        "end_nav": end_nav,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "period_high_nav": period_high_nav,
        "period_high_date": period_high_date,
        "period_low_nav": period_low_nav,
        "period_low_date": period_low_date,
        "max_drawdown_pct": max_drawdown_pct,
        "annualized_volatility_pct": ann_vol_pct
    }


def execute_nav_pull(
    query_or_code: str,
    period: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    select: Optional[int] = None,
    auto_direct_growth: bool = True
) -> Dict[str, Any]:
    # 1. Resolve Scheme
    resolved = resolve_fund(query_or_code, auto_direct_growth=auto_direct_growth)
    
    if resolved["status"] == "AMBIGUOUS" and select:
        matches = resolved.get("matches", [])
        idx = select - 1
        if 0 <= idx < len(matches):
            chosen = matches[idx]
            meta = fetch_scheme_meta(chosen["scheme_code"])
            resolved = {
                "status": "RESOLVED",
                "selection_mode": "MANUAL_USER_SELECTION",
                "selected": meta if meta else chosen,
                "matches": matches,
                "typo_corrections": resolved.get("typo_corrections", [])
            }
        else:
            return {"status": "ERROR", "message": f"Invalid selection {select}. Must be 1-{len(matches)}"}

    if resolved["status"] != "RESOLVED":
        return resolved

    scheme_info = resolved["selected"]
    scheme_code = scheme_info["scheme_code"]

    # 2. Parse Date Horizon
    s_iso, e_iso, horizon_label = parse_horizon_or_dates(
        period_str=period,
        start_date=start_date,
        end_date=end_date
    )

    # 3. Fetch from Swagger endpoint
    raw_resp = fetch_nav_data(scheme_code, start_date=s_iso, end_date=e_iso)
    if not raw_resp or "data" not in raw_resp:
        return {
            "status": "ERROR",
            "message": f"Could not retrieve NAV data for scheme {scheme_code} from mfapi.in"
        }

    nav_records = raw_resp.get("data", [])
    if not nav_records:
        return {
            "status": "EMPTY",
            "message": f"No NAV records returned for scheme {scheme_code} for horizon: {horizon_label}",
            "meta": raw_resp.get("meta", scheme_info),
            "horizon_label": horizon_label,
            "startDate_queried": s_iso,
            "endDate_queried": e_iso
        }

    # 4. Compute Metrics
    metrics = compute_performance_metrics(nav_records)

    return {
        "status": "SUCCESS",
        "scheme_code": scheme_code,
        "meta": raw_resp.get("meta", scheme_info),
        "horizon_label": horizon_label,
        "startDate_queried": s_iso,
        "endDate_queried": e_iso,
        "metrics": metrics,
        "data": nav_records,
        "typo_corrections": resolved.get("typo_corrections", [])
    }


def main():
    parser = argparse.ArgumentParser(description="Pull mutual fund NAV data via mfapi.in Swagger API.")
    parser.add_argument("--query", "-q", type=str, help="Fund name or scheme code (e.g. 'HDFV midcap', 'parag parikh flexicap', '118989')")
    parser.add_argument("--scheme-code", "-s", type=int, help="AMFI scheme code directly (e.g. 118989, 122639)")
    parser.add_argument("--period", "-p", type=str, help="Horizon (e.g. 'last 15 months', 'since inception', '3 years', 'ytd')")
    parser.add_argument("--start-date", type=str, help="Explicit start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="Explicit end date (YYYY-MM-DD)")
    parser.add_argument("--select", type=int, help="Selection index if query is ambiguous (1-based)")
    parser.add_argument("--all", action="store_true", help="Do not filter for Direct Growth plans")
    parser.add_argument("--csv", type=str, help="Filepath to export NAV records to CSV")
    parser.add_argument("--html", type=str, help="Filepath to export interactive HTML Chart.js dashboard")
    parser.add_argument("--output-dir", "-o", type=str, help="Directory to save generated CSV and HTML reports")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    target_query = str(args.scheme_code) if args.scheme_code else args.query
    if not target_query:
        print("❌ Error: Either --query/-q or --scheme-code/-s must be provided.", file=sys.stderr)
        sys.exit(1)

    result = execute_nav_pull(
        query_or_code=target_query,
        period=args.period,
        start_date=args.start_date,
        end_date=args.end_date,
        select=args.select,
        auto_direct_growth=not args.all
    )

    if result.get("status") == "AMBIGUOUS":
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("typo_corrections"):
                print(f"ℹ️ Typo Correction: {', '.join(result['typo_corrections'])}")
            print(f"⚠️ Ambiguous Search Query: '{result['query']}'")
            print(f"Found {result['total_matches']} matching funds. Please select an option:")
            for idx, m in enumerate(result["matches"], 1):
                print(f"   [{idx}] Scheme Code: {m['scheme_code']} | {m['scheme_name']}")
            print("\nPass --select <number> to specify an option.")
        return

    if result.get("status") != "SUCCESS":
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ {result.get('message', 'Failed to retrieve NAV data')}", file=sys.stderr)
        sys.exit(1)

    # Optional exports
    code = result["scheme_code"]
    out_dir = Path(args.output_dir).resolve() if args.output_dir else Path.cwd()
    
    csv_path = None
    if args.csv:
        csv_path = Path(args.csv).resolve()
    elif args.output_dir:
        csv_path = out_dir / f"{code}_nav_history.csv"

    if csv_path:
        export_to_csv(result, csv_path)
        print(f"📁 CSV exported: {csv_path}", file=sys.stderr)

    html_path = None
    if args.html:
        html_path = Path(args.html).resolve()
    elif args.output_dir:
        html_path = out_dir / f"{code}_nav_chart.html"

    if html_path:
        html_content = generate_interactive_html(result)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_content, encoding="utf-8")
        print(f"🌐 HTML Chart exported: {html_path}", file=sys.stderr)

    if args.json:
        # Trim giant data array in stdout JSON unless requested
        summary_res = dict(result)
        summary_res["sample_records_count"] = len(summary_res["data"])
        summary_res["data"] = summary_res["data"][:5]
        print(json.dumps(summary_res, indent=2))
        return

    # Print markdown report
    md_report = generate_markdown_report(result)
    print("\n" + md_report)


if __name__ == "__main__":
    main()
