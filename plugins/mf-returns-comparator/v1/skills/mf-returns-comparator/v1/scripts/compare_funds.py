#!/usr/bin/env python3
"""
compare_funds.py - Multi-Fund NAV Returns & Risk Metrics Comparator
Compares historical performance across 2 or more mutual funds over a given timeframe.
Depends on and utilizes the 'mf-nav-puller' skill for scheme resolution and NAV fetching.
Auto-resolves Direct Plan - Growth options, aligns trading sessions, rebases to 100,
computes CAGR, Max Drawdown, Volatility, and Sharpe Ratio, and generates side-by-side
Markdown tables, CSV datasets, and interactive Chart.js overlay dashboards.
"""

import sys
import os
import json
import math
import argparse
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Workspace Discovery: Import helper modules from mf-nav-puller skill
# ---------------------------------------------------------------------------
PULLER_CANDIDATE_PATHS = [
    os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../mf-nav-puller/v1/skills/mf-nav-puller/v1/scripts")),
    os.path.abspath(os.path.join(SCRIPT_DIR, "../../../../../skills/mf-nav-puller/latest/scripts")),
    os.path.abspath(os.path.join(os.getcwd(), "skills/mf-nav-puller/latest/scripts")),
    os.path.abspath(os.path.join(os.getcwd(), "plugins/mf-nav-puller/v1/skills/mf-nav-puller/v1/scripts")),
]

nav_puller_dir = None
for p in PULLER_CANDIDATE_PATHS:
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, "pull_nav.py")):
        nav_puller_dir = p
        break

if not nav_puller_dir:
    print(f"❌ Error: Required dependency 'mf-nav-puller' skill scripts not found.", file=sys.stderr)
    print(f"Checked candidate locations:\n" + "\n".join(f" - {p}" for p in PULLER_CANDIDATE_PATHS), file=sys.stderr)
    sys.exit(1)

if nav_puller_dir not in sys.path:
    sys.path.insert(0, nav_puller_dir)

try:
    from resolve_scheme import resolve_fund, fetch_scheme_meta
    from pull_nav import fetch_nav_data
    from date_parser import parse_horizon_or_dates
except ImportError as e:
    print(f"❌ Error importing from mf-nav-puller ({nav_puller_dir}): {e}", file=sys.stderr)
    sys.exit(1)


PALETTE = [
    {"border": "rgb(37, 99, 235)", "bg": "rgba(37, 99, 235, 0.1)", "name": "Blue"},
    {"border": "rgb(16, 185, 129)", "bg": "rgba(16, 185, 129, 0.1)", "name": "Emerald"},
    {"border": "rgb(245, 158, 11)", "bg": "rgba(245, 158, 11, 0.1)", "name": "Amber"},
    {"border": "rgb(239, 68, 68)", "bg": "rgba(239, 68, 68, 0.1)", "name": "Red"},
    {"border": "rgb(168, 85, 247)", "bg": "rgba(168, 85, 247, 0.1)", "name": "Purple"},
    {"border": "rgb(6, 182, 212)", "bg": "rgba(6, 182, 212, 0.1)", "name": "Cyan"}
]


def calculate_fund_metrics(records: List[Dict[str, Any]], risk_free_rate: float = 6.5) -> Dict[str, Any]:
    """
    records is ordered chronologically: oldest first, newest last.
    """
    if not records:
        return {}

    start_rec = records[0]
    end_rec = records[-1]
    start_nav = start_rec["nav"]
    end_nav = end_rec["nav"]

    start_dt = datetime.strptime(start_rec["date"], "%d-%m-%Y").date()
    end_dt = datetime.strptime(end_rec["date"], "%d-%m-%Y").date()
    total_days = max(1, (end_dt - start_dt).days)

    total_return_pct = ((end_nav - start_nav) / start_nav) * 100.0

    # Annualized return (CAGR)
    if total_days >= 30 and start_nav > 0 and end_nav > 0:
        cagr_pct = ((end_nav / start_nav) ** (365.25 / total_days) - 1.0) * 100.0
    else:
        cagr_pct = total_return_pct

    # High / Low / Drawdowns
    high_nav = -1.0
    high_date = ""
    low_nav = float("inf")
    low_date = ""

    peak = -1.0
    max_drawdown = 0.0

    daily_returns = []

    for i, r in enumerate(records):
        nav = r["nav"]
        dt = r["date"]

        if nav > high_nav:
            high_nav = nav
            high_date = dt
        if nav < low_nav:
            low_nav = nav
            low_date = dt

        if nav > peak:
            peak = nav
        else:
            dd = ((nav - peak) / peak) * 100.0
            if dd < max_drawdown:
                max_drawdown = dd

        if i > 0:
            prev_nav = records[i - 1]["nav"]
            if prev_nav > 0:
                daily_returns.append((nav - prev_nav) / prev_nav)

    # Volatility & Sharpe
    if len(daily_returns) > 1:
        mean_r = sum(daily_returns) / len(daily_returns)
        var_r = sum((r - mean_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        daily_vol = math.sqrt(var_r)
        annualized_vol = daily_vol * math.sqrt(252) * 100.0
    else:
        annualized_vol = 0.0

    sharpe = (cagr_pct - risk_free_rate) / annualized_vol if annualized_vol > 0 else 0.0

    return {
        "start_date": start_rec["date"],
        "end_date": end_rec["date"],
        "start_nav": start_nav,
        "end_nav": end_nav,
        "total_days": total_days,
        "records_count": len(records),
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "high_nav": high_nav,
        "high_date": high_date,
        "low_nav": low_nav,
        "low_date": low_date,
        "max_drawdown_pct": max_drawdown,
        "annualized_volatility_pct": annualized_vol,
        "sharpe_ratio": sharpe
    }


def generate_comparison_html(
    funds_data: List[Dict[str, Any]],
    aligned_dates: List[str],
    horizon_label: str,
    output_path: str
):
    """
    Renders an interactive Chart.js overlay comparison with normalized NAV (Base 100).
    """
    labels_json = json.dumps(aligned_dates)
    datasets = []

    for idx, f in enumerate(funds_data):
        palette = PALETTE[idx % len(PALETTE)]
        datasets.append({
            "label": f["meta"]["scheme_name"],
            "code": f["meta"]["scheme_code"],
            "data": f["normalized_navs"],
            "raw_navs": f["raw_navs"],
            "borderColor": palette["border"],
            "backgroundColor": palette["bg"],
            "borderWidth": 2,
            "pointRadius": 0,
            "pointHoverRadius": 5,
            "tension": 0.1,
            "fill": False
        })

    datasets_json = json.dumps(datasets)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mutual Fund Historical Comparison - {horizon_label}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --border-card: rgba(255, 255, 255, 0.1);
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-red: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
        body {{
            background-color: var(--bg-base);
            color: var(--text-main);
            padding: 2rem 1.5rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        header {{
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-card);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        h1 {{ font-size: 1.85rem; font-weight: 700; color: #fff; }}
        .badge {{
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 14px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
        }}
        .card-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .card-stat {{
            display: flex;
            justify-content: space-between;
            padding: 0.4rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }}
        .card-stat:last-child {{ border-bottom: none; }}
        .card-stat .label {{ color: var(--text-sub); }}
        .card-stat .value {{ font-weight: 600; font-family: monospace; font-size: 0.95rem; }}
        .pos {{ color: var(--accent-green); }}
        .neg {{ color: var(--accent-red); }}
        .chart-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            padding: 1.5rem;
            height: 520px;
            margin-bottom: 2rem;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .subtext {{ color: var(--text-sub); font-size: 0.85rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-card);
        }}
        th {{
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-sub);
            font-weight: 600;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>📊 Mutual Funds Historical Return Comparison</h1>
            <p class="subtext">Powered by mf-returns-comparator & mf-nav-puller skills</p>
        </div>
        <div>
            <span class="badge">Horizon: {horizon_label}</span>
            <span class="badge" style="margin-left: 0.5rem;">{len(aligned_dates)} Common Trading Days</span>
        </div>
    </header>

    <div class="grid">
"""

    for idx, f in enumerate(funds_data):
        m = f["metrics"]
        meta = f["meta"]
        pal = PALETTE[idx % len(PALETTE)]
        html_content += f"""
        <div class="card" style="border-top: 4px solid {pal['border']};">
            <div class="card-title">
                <span title="{meta['scheme_name']}">{meta['scheme_name'][:32]}...</span>
                <span style="font-size: 0.75rem; color: {pal['border']};">Code: {meta['scheme_code']}</span>
            </div>
            <div class="card-stat">
                <span class="label">Total Return</span>
                <span class="value {'pos' if m['total_return_pct'] >= 0 else 'neg'}">+{m['total_return_pct']:.2f}%</span>
            </div>
            <div class="card-stat">
                <span class="label">Annualized CAGR</span>
                <span class="value {'pos' if m['cagr_pct'] >= 0 else 'neg'}">+{m['cagr_pct']:.2f}%</span>
            </div>
            <div class="card-stat">
                <span class="label">Start NAV ({m['start_date']})</span>
                <span class="value">₹{m['start_nav']:.4f}</span>
            </div>
            <div class="card-stat">
                <span class="label">End NAV ({m['end_date']})</span>
                <span class="value">₹{m['end_nav']:.4f}</span>
            </div>
            <div class="card-stat">
                <span class="label">Max Drawdown</span>
                <span class="value neg">{m['max_drawdown_pct']:.2f}%</span>
            </div>
            <div class="card-stat">
                <span class="label">Annualized Volatility (σ)</span>
                <span class="value">{m['annualized_volatility_pct']:.2f}%</span>
            </div>
            <div class="card-stat">
                <span class="label">Sharpe Ratio (Rf=6.5%)</span>
                <span class="value">{m['sharpe_ratio']:.2f}</span>
            </div>
        </div>
        """

    html_content += f"""
    </div>

    <div class="chart-box">
        <div class="chart-header">
            <div>
                <h3>Growth of ₹100 Invested (Rebased)</h3>
                <span class="subtext">All funds normalized to 100 on start date ({funds_data[0]['metrics']['start_date']})</span>
            </div>
        </div>
        <div style="position: relative; height: 420px;">
            <canvas id="compChart"></canvas>
        </div>
    </div>

    <div class="card" style="margin-bottom: 2rem;">
        <h3 style="margin-bottom: 0.75rem;">📋 Side-by-Side Comparison Matrix</h3>
        <table>
            <thead>
                <tr>
                    <th>Scheme Name</th>
                    <th>AMFI Code</th>
                    <th>Total Return</th>
                    <th>Annualized CAGR</th>
                    <th>Max Drawdown</th>
                    <th>Volatility (σ)</th>
                    <th>Sharpe Ratio</th>
                    <th>Period High</th>
                    <th>Period Low</th>
                </tr>
            </thead>
            <tbody>
    """

    for f in funds_data:
        m = f["metrics"]
        meta = f["meta"]
        html_content += f"""
                <tr>
                    <td><strong>{meta['scheme_name']}</strong></td>
                    <td><code>{meta['scheme_code']}</code></td>
                    <td class="{'pos' if m['total_return_pct'] >= 0 else 'neg'}">+{m['total_return_pct']:.2f}%</td>
                    <td class="{'pos' if m['cagr_pct'] >= 0 else 'neg'}">+{m['cagr_pct']:.2f}%</td>
                    <td class="neg">{m['max_drawdown_pct']:.2f}%</td>
                    <td>{m['annualized_volatility_pct']:.2f}%</td>
                    <td><strong>{m['sharpe_ratio']:.2f}</strong></td>
                    <td>₹{m['high_nav']:.2f} ({m['high_date']})</td>
                    <td>₹{m['low_nav']:.2f} ({m['low_date']})</td>
                </tr>
        """

    html_content += f"""
            </tbody>
        </table>
    </div>
</div>

<script>
    const labels = {labels_json};
    const rawDatasets = {datasets_json};

    const ctx = document.getElementById('compChart').getContext('2d');
    const chart = new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: labels,
            datasets: rawDatasets
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                mode: 'index',
                intersect: false
            }},
            plugins: {{
                legend: {{
                    position: 'top',
                    labels: {{
                        color: '#f8fafc',
                        font: {{ family: 'Inter', size: 12 }},
                        boxWidth: 16
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#60a5fa',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {{
                        label: function(ctx) {{
                            const dataset = rawDatasets[ctx.datasetIndex];
                            const rebasedVal = ctx.parsed.y.toFixed(2);
                            const rawNav = dataset.raw_navs[ctx.dataIndex].toFixed(2);
                            const gain = (rebasedVal - 100).toFixed(2);
                            const sign = gain >= 0 ? '+' : '';
                            return `${{dataset.label.split('-')[0].trim()}}: ₹${{rawNav}} (${{sign}}${{gain}}% rebased: ${{rebasedVal}})`;
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                    ticks: {{ color: '#94a3b8', maxTicksLimit: 12 }}
                }},
                y: {{
                    grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                    ticks: {{
                        color: '#94a3b8',
                        callback: function(val) {{ return '₹' + val; }}
                    }}
                }}
            }}
        }}
    }});
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def export_comparison_csv(
    funds_data: List[Dict[str, Any]],
    aligned_dates: List[str],
    output_path: str
):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    headers = ["Date"]
    for f in funds_data:
        code = f["meta"]["scheme_code"]
        name_clean = f["meta"]["scheme_name"].split("-")[0].strip().replace(" ", "_")
        headers.extend([f"{name_clean}_{code}_NAV", f"{name_clean}_{code}_Rebased100"])

    rows = []
    for i, dt in enumerate(aligned_dates):
        row = [dt]
        for f in funds_data:
            row.append(f"{f['raw_navs'][i]:.4f}")
            row.append(f"{f['normalized_navs'][i]:.4f}")
        rows.append(",".join(row))

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(",".join(headers) + "\n")
        out.write("\n".join(rows) + "\n")


def compare_funds(
    fund_queries: List[str],
    period: Optional[str] = "last 5 years",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    output_dir: Optional[str] = None,
    csv_path: Optional[str] = None,
    html_path: Optional[str] = None
) -> Dict[str, Any]:
    resolved_funds = []
    
    # 1. Resolve each fund query using mf-nav-puller's resolve_fund
    for q in fund_queries:
        res = resolve_fund(q, auto_direct_growth=True)
        if res.get("status") != "RESOLVED":
            print(f"❌ Could not resolve fund query '{q}': {res.get('message', 'Ambiguous or not found')}", file=sys.stderr)
            if "matches" in res:
                print(f"   Candidates for '{q}':", file=sys.stderr)
                for idx, m in enumerate(res["matches"][:5], 1):
                    print(f"   [{idx}] {m.get('scheme_code')} - {m.get('scheme_name')}", file=sys.stderr)
            sys.exit(1)
        resolved_funds.append(res["selected"])

    # 2. Parse time horizon using mf-nav-puller's parse_horizon_or_dates
    s_dt, e_dt, label = parse_horizon_or_dates(period or "last 5 years", start_date, end_date)

    # 3. Fetch data for each fund using mf-nav-puller's fetch_nav_data
    fund_records_map = {}
    for meta in resolved_funds:
        code = meta["scheme_code"]
        raw_resp = fetch_nav_data(code, start_date=s_dt, end_date=e_dt)
        if not raw_resp:
            print(f"❌ Failed to fetch NAV data for scheme {code}", file=sys.stderr)
            sys.exit(1)
        raw_list = raw_resp.get("data", [])
        if not raw_list:
            print(f"❌ No records found for {meta['scheme_name']} in period {label}", file=sys.stderr)
            sys.exit(1)

        # Parse float nav and reverse to chronological (oldest first)
        parsed_records = []
        date_dict = {}
        for r in reversed(raw_list):
            try:
                val = float(r["nav"])
                dt = r["date"]
                parsed_records.append({"date": dt, "nav": val})
                date_dict[dt] = val
            except (ValueError, TypeError):
                continue

        fund_records_map[code] = {
            "meta": meta,
            "raw_records": parsed_records,
            "date_dict": date_dict
        }

    # 4. Find common dates across all funds
    common_dates_set = None
    for code, data in fund_records_map.items():
        if common_dates_set is None:
            common_dates_set = set(data["date_dict"].keys())
        else:
            common_dates_set = common_dates_set.intersection(set(data["date_dict"].keys()))

    if not common_dates_set:
        print("❌ No overlapping trading dates found among the selected funds!", file=sys.stderr)
        sys.exit(1)

    # Sort common dates chronologically
    sorted_common_dates = sorted(
        list(common_dates_set),
        key=lambda d: datetime.strptime(d, "%d-%m-%Y")
    )

    # 5. Extract aligned series and compute normalized NAVs (Base 100)
    funds_data = []
    for meta in resolved_funds:
        code = meta["scheme_code"]
        d_dict = fund_records_map[code]["date_dict"]
        aligned_recs = [{"date": dt, "nav": d_dict[dt]} for dt in sorted_common_dates]
        start_nav = aligned_recs[0]["nav"]
        normalized_navs = [round((r["nav"] / start_nav) * 100.0, 4) for r in aligned_recs]
        raw_navs = [r["nav"] for r in aligned_recs]
        metrics = calculate_fund_metrics(aligned_recs)

        funds_data.append({
            "meta": meta,
            "metrics": metrics,
            "aligned_records": aligned_recs,
            "normalized_navs": normalized_navs,
            "raw_navs": raw_navs
        })

    # 6. Export outputs
    out_dir = output_dir or "reports/fund_comparison"
    actual_csv = csv_path or os.path.join(out_dir, "nav_comparison.csv")
    actual_html = html_path or os.path.join(out_dir, "nav_comparison.html")

    export_comparison_csv(funds_data, sorted_common_dates, actual_csv)
    generate_comparison_html(funds_data, sorted_common_dates, label, actual_html)

    return {
        "status": "SUCCESS",
        "horizon_label": label,
        "start_date": sorted_common_dates[0],
        "end_date": sorted_common_dates[-1],
        "common_trading_days": len(sorted_common_dates),
        "funds": funds_data,
        "csv_path": os.path.abspath(actual_csv),
        "html_path": os.path.abspath(actual_html)
    }


def main():
    parser = argparse.ArgumentParser(description="Compare historical NAV returns and risk metrics for multiple funds.")
    parser.add_argument("--funds", "-f", nargs="+", required=True, help="Fund names or scheme codes (e.g. 'DSP flexicap' 'PPFAS flexicap' 'HDFC flexicap')")
    parser.add_argument("--period", "-p", type=str, default="last 5 years", help="Comparison horizon (e.g. 'last 5 years', 'last 3 years', 'since inception')")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", "-o", type=str, default="reports/flexicap_comparison", help="Output directory for CSV and HTML reports")
    parser.add_argument("--csv", type=str, help="Custom CSV output path")
    parser.add_argument("--html", type=str, help="Custom HTML output path")
    parser.add_argument("--json", action="store_true", help="Print summary JSON")
    args = parser.parse_args()

    result = compare_funds(
        fund_queries=args.funds,
        period=args.period,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        csv_path=args.csv,
        html_path=args.html
    )

    if args.json:
        clean_funds = []
        for f in result["funds"]:
            clean_funds.append({
                "scheme_name": f["meta"]["scheme_name"],
                "scheme_code": f["meta"]["scheme_code"],
                "metrics": f["metrics"]
            })
        print(json.dumps({
            "horizon": result["horizon_label"],
            "common_trading_days": result["common_trading_days"],
            "csv_path": result["csv_path"],
            "html_path": result["html_path"],
            "funds": clean_funds
        }, indent=2))
        return

    # Print Markdown Summary
    print(f"\n# 📊 Historical Returns & Risk Comparison: {result['horizon_label']}")
    print(f"**Period:** `{result['start_date']}` to `{result['end_date']}` | **Common Trading Days:** `{result['common_trading_days']}`\n")

    print("## 📌 Side-by-Side Performance Matrix")
    print("| Performance & Risk Metric | " + " | ".join([f["meta"]["scheme_name"].split("-")[0].strip() for f in result["funds"]]) + " |")
    print("| :--- | " + " | ".join([":---:" for _ in result["funds"]]) + " |")

    # Rows
    print("| **AMFI Scheme Code** | " + " | ".join([f"`{f['meta']['scheme_code']}`" for f in result["funds"]]) + " |")
    print("| **Initial NAV** | " + " | ".join([f"₹{f['metrics']['start_nav']:.4f}" for f in result["funds"]]) + " |")
    print("| **Latest NAV** | " + " | ".join([f"₹{f['metrics']['end_nav']:.4f}" for f in result["funds"]]) + " |")
    print("| **Cumulative Return** | " + " | ".join([f"**+{f['metrics']['total_return_pct']:.2f}%**" for f in result["funds"]]) + " |")
    print("| **Annualized CAGR** | " + " | ".join([f"**+{f['metrics']['cagr_pct']:.2f}%**" for f in result["funds"]]) + " |")
    print("| **Maximum Drawdown (MaxDD)** | " + " | ".join([f"`{f['metrics']['max_drawdown_pct']:.2f}%`" for f in result["funds"]]) + " |")
    print("| **Annualized Volatility (σ)** | " + " | ".join([f"`{f['metrics']['annualized_volatility_pct']:.2f}%`" for f in result["funds"]]) + " |")
    print("| **Sharpe Ratio (Rf=6.5%)** | " + " | ".join([f"**{f['metrics']['sharpe_ratio']:.2f}**" for f in result["funds"]]) + " |")
    print("| **Period High NAV** | " + " | ".join([f"₹{f['metrics']['high_nav']:.2f}" for f in result["funds"]]) + " |")
    print("| **Period Low NAV** | " + " | ".join([f"₹{f['metrics']['low_nav']:.2f}" for f in result["funds"]]) + " |")

    print(f"\n📁 **CSV Dataset:** {result['csv_path']}")
    print(f"🌐 **Interactive HTML Chart:** {result['html_path']}\n")


if __name__ == "__main__":
    main()

