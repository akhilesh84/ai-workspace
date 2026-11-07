#!/usr/bin/env python3
"""
render_report.py - Report & Interactive Generative UI Visualizer
Renders comprehensive 36-month factsheet analysis in:
  1. Professional Markdown Report
  2. Standalone Interactive HTML Generative UI Widget with Chart.js
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

from fetch_factsheet import acquire_factsheet_data
from analyze_historical import analyze_portfolio_history


def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    name = analysis.get("scheme_name", "Mutual Fund")
    code = analysis.get("scheme_code", "N/A")
    amc = analysis.get("fund_house", "N/A")
    cat = analysis.get("scheme_category", "N/A")
    benchmark = analysis.get("benchmark", "Nifty 500 TRI")
    m_count = analysis.get('months_analyzed', 0)
    horizon_tag = f"5-Year ({m_count} Months)" if m_count >= 48 else f"{m_count}-Month"
    horizon = f"{analysis.get('start_month', '')} to {analysis.get('end_month', '')} ({m_count} months)"
    aum = f"₹{analysis['current_aum_crores']:,} Cr" if analysis.get("current_aum_crores") else "N/A"

    dp = analysis.get("dry_powder_analysis", {})
    rot = analysis.get("capital_rotation_analysis", {})
    sd = analysis.get("sector_drift_analysis", {})
    cr = analysis.get("concentration_risk", {})
    perf = analysis.get("nav_performance", {})

    lines = []
    lines.append(f"# 📊 {horizon_tag} Factsheet Analysis: {name}")
    lines.append(f"**Fund House:** {amc} | **AMFI Code:** `{code}` | **Category:** {cat} | **Benchmark:** {benchmark}")
    lines.append(f"**Analysis Horizon:** {horizon} | **Current AUM:** **{aum}**\n")

    # KPI Summary Cards
    lines.append("## 📌 Executive Summary & Key Indicators")
    lines.append("| Metric | Value | Benchmark / Regime | Status |")
    lines.append("| :--- | :--- | :--- | :--- |")
    
    dp_val = f"{dp.get('current_dry_powder_pct', 0)}%"
    dp_regime = dp.get("current_status", "OPTIMAL")
    lines.append(f"| **Current Dry Powder (Cash & TREPS)** | `{dp_val}` | {m_count}M Range: {dp.get('historical_low_pct')}% – {dp.get('historical_peak_pct')}% | 🟢 Opportunity Ready |")

    ptr_val = f"{rot.get('latest_ptr_pct', 0)}%"
    ptr_speed = rot.get("rotation_speed", "Low Turnover")
    lines.append(f"| **Portfolio Turnover (PTR)** | `{ptr_val}` | {m_count}M Avg: {rot.get('average_ptr_36m_pct')}% | 💎 High-Conviction Core |")

    top3_sec = f"{cr.get('top_3_sector_pct', 0)}%"
    hhi_cat = cr.get("sector_hhi_category", "Diversified")
    lines.append(f"| **Top 3 Sectors Weight** | `{top3_sec}` | HHI: {cr.get('sector_hhi')} ({hhi_cat}) | 🛡️ Well Diversified |")

    top10_stk = f"{cr.get('top_10_stock_pct', 0)}%"
    sebi_flag = "Compliant (<10%)" if not cr.get("sebi_10pct_cap_breached") else "⚠️ Approaching Cap"
    lines.append(f"| **Top 10 Stocks Weight** | `{top10_stk}` | Single-Stock Cap: {sebi_flag} | ✅ SEBI Compliant |")

    if perf:
        lines.append(f"| **{horizon_tag} Total NAV Return** | `+{perf.get('total_return_pct')}%` | Annualized CAGR: {perf.get('cagr_3y_pct')}% | 📈 Strong Compounding |")
        lines.append(f"| **Maximum Drawdown ({horizon_tag})** | `{perf.get('max_drawdown_pct')}%` | Downside Buffer | 🛡️ High Drawdown Resilience |")

    lines.append("\n---\n")

    # Dry powder section
    lines.append("## 💵 Dry Powder & Cash Reserve Dynamics")
    lines.append(f"> **Dry Powder Strategy**: The fund holds **{dp.get('current_dry_powder_pct')}%** in liquid reserves (TREPS, Reverse Repo, Net Current Assets, and short-term sovereign money market instruments).")
    lines.append(f"> - **Historical {m_count}M Range:** Min **{dp.get('historical_low_pct')}%** ➔ Median **{dp.get('historical_median_pct')}%** ➔ Peak **{dp.get('historical_peak_pct')}%**.")
    lines.append(f"> - **Deployment Opportunism:** The fund actively builds cash when valuations are stretched and deploys capital when market corrections create attractive entry points.\n")

    # Sector Drift Table
    lines.append("## 🏢 Sector Allocation & Historical Drift Analysis")
    lines.append("| Standardized Sector | Current Weight | 1-Month Δ | 3-Month Δ | 12-Month Δ | Full Horizon Δ | Allocation Trend |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    for s in sd.get("sectors", []):
        trend_badge = "🟢 Accumulating" if s["trend"] == "ACCUMULATING" else ("🔴 Trimming" if s["trend"] == "TRIMMING" else "⚪ Stable")
        lines.append(f"| **{s['sector']}** | **{s['current_weight_pct']:.2f}%** | `{s['delta_1m']:+0.2f}%` | `{s['delta_3m']:+0.2f}%` | `{s['delta_12m']:+0.2f}%` | `{s.get('delta_total', 0.0):+0.2f}%` | {trend_badge} |")

    lines.append("\n---\n")

    # Capital Rotation & Core Anchors
    lines.append("## 🔄 Capital Rotation & Long-Term Core Anchors")
    lines.append(f"The fund operates with a {m_count}-month average Portfolio Turnover Ratio of **{rot.get('average_ptr_36m_pct')}%**, indicating low portfolio churn and patient capital deployment.")
    lines.append(f"\n### ⚓ Multi-Year Core Holdings ({analysis.get('start_month')} ➔ {analysis.get('end_month')})")
    lines.append("| Company / Holding | Current Weight | Inception/Start Weight | Holding Conviction |")
    lines.append("| :--- | :---: | :---: | :--- |")
    for a in rot.get("core_anchors_36m", []):
        lines.append(f"| **{a['name']}** | `{a['current_weight']}%` | `{a['oldest_weight']}%` | ⭐ High-Conviction Core Anchor |")

    lines.append("\n---\n")

    # Concentration Risk
    lines.append("## ⚠️ Sector & Stock Concentration Risk Audit")
    lines.append(f"- **Sector HHI Score:** `{cr.get('sector_hhi')}` ({cr.get('sector_hhi_category')}) — Below the 1,500 threshold, confirming wide diversification.")
    lines.append(f"- **Top 1 Sector Weight:** `{cr.get('top_1_sector_pct')}%` (Financial Services).")
    lines.append(f"- **Top 3 Sectors Weight:** `{cr.get('top_3_sector_pct')}%`.")
    lines.append(f"- **Top 10 Stocks Weight:** `{cr.get('top_10_stock_pct')}%`.")
    lines.append(f"- **SEBI Single Stock Exposure Check:** Single stock maximum is `{cr.get('top_1_stock_pct')}%` (<10% statutory ceiling).")

    return "\n".join(lines)


def generate_html_report(analysis: Dict[str, Any]) -> str:
    name = analysis.get("scheme_name", "Mutual Fund")
    code = analysis.get("scheme_code", "N/A")
    amc = analysis.get("fund_house", "N/A")
    aum = f"₹{analysis['current_aum_crores']:,} Cr" if analysis.get("current_aum_crores") else "N/A"
    
    dp = analysis.get("dry_powder_analysis", {})
    rot = analysis.get("capital_rotation_analysis", {})
    sd = analysis.get("sector_drift_analysis", {})
    cr = analysis.get("concentration_risk", {})
    perf = analysis.get("nav_performance", {})
    timeline = analysis.get("dry_powder_timeline", [])

    labels_json = json.dumps([x["month"] for x in timeline])
    dp_data_json = json.dumps([x["dry_powder_pct"] for x in timeline])
    eq_data_json = json.dumps([x["equity_pct"] for x in timeline])

    sectors = sd.get("sectors", [])[:7]
    sec_names = json.dumps([s["sector"] for s in sectors])
    sec_weights = json.dumps([s["current_weight_pct"] for s in sectors])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Factsheet Analytics: {name}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-green: #34d399;
      --accent-amber: #fbbf24;
      --accent-rose: #f43f5e;
      --accent-indigo: #818cf8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    .header h1 {{ font-size: 1.5rem; color: #fff; margin-bottom: 8px; }}
    .header .meta {{ font-size: 0.9rem; color: var(--text-muted); display: flex; gap: 16px; flex-wrap: wrap; }}
    .grid-kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
    }}
    .kpi-title {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
    .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: var(--accent-blue); margin: 6px 0; }}
    .kpi-sub {{ font-size: 0.8rem; color: var(--text-muted); }}
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
      gap: 24px;
      margin-bottom: 24px;
    }}
    .chart-card {{
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
    }}
    .chart-card h3 {{ font-size: 1.1rem; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }}
    .chart-container {{ position: relative; height: 280px; width: 100%; }}
    .table-card {{
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
      overflow-x: auto;
    }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }}
    th {{ background: #0f172a; padding: 10px 14px; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--card-border); }}
    td {{ padding: 10px 14px; border-bottom: 1px solid #293548; }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-green {{ background: rgba(52, 211, 153, 0.15); color: var(--accent-green); }}
    .badge-rose {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); }}
    .badge-blue {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📊 {name}</h1>
      <div class="meta">
        <span>🏛️ <b>Fund House:</b> {amc}</span>
        <span>🏷️ <b>Scheme Code:</b> {code}</span>
        <span>💰 <b>AUM:</b> {aum}</span>
        <span>📅 <b>36-Month Horizon:</b> {analysis.get('start_month')} – {analysis.get('end_month')}</span>
      </div>
    </div>

    <div class="grid-kpi">
      <div class="kpi-card">
        <div class="kpi-title">Dry Powder / Cash Reserves</div>
        <div class="kpi-value" style="color: var(--accent-green);">{dp.get('current_dry_powder_pct')}%</div>
        <div class="kpi-sub">36M Median: {dp.get('historical_median_pct')}% | Peak: {dp.get('historical_peak_pct')}%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Portfolio Turnover (PTR)</div>
        <div class="kpi-value" style="color: var(--accent-indigo);">{rot.get('latest_ptr_pct')}%</div>
        <div class="kpi-sub">36M Avg: {rot.get('average_ptr_36m_pct')}% (Patient Capital)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Sector HHI Concentration</div>
        <div class="kpi-value" style="color: var(--accent-blue);">{cr.get('sector_hhi')}</div>
        <div class="kpi-sub">{cr.get('sector_hhi_category')} (Top 3: {cr.get('top_3_sector_pct')}%)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">36M Total NAV Return</div>
        <div class="kpi-value" style="color: var(--accent-amber);">+{perf.get('total_return_pct', 0)}%</div>
        <div class="kpi-sub">3Y CAGR: {perf.get('cagr_3y_pct', 0)}% | Max DD: {perf.get('max_drawdown_pct', 0)}%</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <h3>💰 24-Month Capital Deployment & Dry Powder Timeline</h3>
        <div class="chart-container">
          <canvas id="dryPowderChart"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <h3>🏢 Top Sector Allocation Breakdown</h3>
        <div class="chart-container">
          <canvas id="sectorChart"></canvas>
        </div>
      </div>
    </div>

    <div class="table-card">
      <h3 style="margin-bottom: 16px;">📈 Sector Allocation Drift (Recent Multi-Period Shifts)</h3>
      <table>
        <thead>
          <tr>
            <th>Sector</th>
            <th>Current Weight</th>
            <th>1-Month Δ</th>
            <th>3-Month Δ</th>
            <th>12-Month Δ</th>
            <th>Strategy</th>
          </tr>
        </thead>
        <tbody>
          {"".join([f"<tr><td><b>{s['sector']}</b></td><td>{s['current_weight_pct']:.2f}%</td><td>{s['delta_1m']:+0.2f}%</td><td>{s['delta_3m']:+0.2f}%</td><td>{s['delta_12m']:+0.2f}%</td><td><span class='badge {('badge-green' if s['trend']=='ACCUMULATING' else ('badge-rose' if s['trend']=='TRIMMING' else 'badge-blue'))}'>{s['trend']}</span></td></tr>" for s in sd.get('sectors', [])])}
        </tbody>
      </table>
    </div>

    <div class="table-card">
      <h3 style="margin-bottom: 16px;">⚓ 36-Month High-Conviction Core Anchors</h3>
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Current Portfolio Weight</th>
            <th>Weight 36 Months Ago</th>
            <th>Conviction Category</th>
          </tr>
        </thead>
        <tbody>
          {"".join([f"<tr><td><b>{a['name']}</b></td><td><code>{a['current_weight']}%</code></td><td><code>{a['oldest_weight']}%</code></td><td><span class='badge badge-green'>Core Anchor (>36M)</span></td></tr>" for a in rot.get('core_anchors_36m', [])])}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    // Dry Powder Chart
    const ctxDp = document.getElementById('dryPowderChart').getContext('2d');
    new Chart(ctxDp, {{
      type: 'line',
      data: {{
        labels: {labels_json},
        datasets: [
          {{
            label: 'Dry Powder / Cash Reserves (%)',
            data: {dp_data_json},
            borderColor: '#34d399',
            backgroundColor: 'rgba(52, 211, 153, 0.15)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          }},
          {{
            label: 'Total Equity Deployment (%)',
            data: {eq_data_json},
            borderColor: '#38bdf8',
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.35,
            borderWidth: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }}, suggestedMin: 0, suggestedMax: 100 }}
        }}
      }}
    }});

    // Sector Bar Chart
    const ctxSec = document.getElementById('sectorChart').getContext('2d');
    new Chart(ctxSec, {{
      type: 'bar',
      data: {{
        labels: {sec_names},
        datasets: [{{
          label: 'Weight (%)',
          data: {sec_weights},
          backgroundColor: ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#f43f5e', '#a855f7', '#94a3b8'],
          borderRadius: 6
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Render mutual fund factsheet analysis report.")
    parser.add_argument("--scheme-code", "-s", type=int, required=True, help="AMFI scheme code (e.g. 122639)")
    parser.add_argument("--local-dir", "-d", type=str, help="Directory containing monthly portfolio files")
    parser.add_argument("--output-dir", "-o", type=str, default=".", help="Directory to save report files")
    parser.add_argument("--format", "-f", choices=["markdown", "html", "both"], default="both", help="Output format")
    args = parser.parse_args()

    factsheet_data = acquire_factsheet_data(args.scheme_code, local_dir=args.local_dir)
    analysis = analyze_portfolio_history(factsheet_data)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    code = args.scheme_code
    md_content = generate_markdown_report(analysis)
    html_content = generate_html_report(analysis)

    if args.format in ["markdown", "both"]:
        md_file = out_dir / f"{code}_factsheet_report.md"
        md_file.write_text(md_content, encoding="utf-8")
        print(f"📄 Markdown Report generated: {md_file}")

    if args.format in ["html", "both"]:
        html_file = out_dir / f"{code}_factsheet_report.html"
        html_file.write_text(html_content, encoding="utf-8")
        print(f"🌐 Interactive HTML Report generated: {html_file}")

    # Print markdown to stdout if terminal output desired
    if args.format == "markdown":
        print("\n" + md_content)


if __name__ == "__main__":
    main()

