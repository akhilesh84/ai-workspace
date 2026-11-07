#!/usr/bin/env python3
"""
render_nav_report.py - Report & Visualization Generator for Mutual Fund NAV Data
Renders:
  1. Executive Markdown Summary with KPI table and sample records
  2. CSV Export for financial modeling / spreadsheets
  3. Interactive HTML Dashboard with Chart.js NAV curve and drawdown indicators
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, List


def generate_markdown_report(result: Dict[str, Any]) -> str:
    meta = result.get("meta", {})
    metrics = result.get("metrics", {})
    horizon = result.get("horizon_label", "Custom Period")
    nav_data = result.get("data", [])

    lines = []
    lines.append(f"# 📈 Mutual Fund NAV Analysis: {meta.get('scheme_name')}")
    lines.append(f"**Fund House:** {meta.get('fund_house')} | **Scheme Code:** `{meta.get('scheme_code')}` | **Category:** {meta.get('scheme_category')}")
    lines.append(f"**Horizon Analyzed:** {horizon} ({metrics.get('trading_days', 0)} trading records)\n")

    # KPI Summary Table
    lines.append("## 📌 Performance & Risk Summary")
    lines.append("| Performance Metric | Value | Reference / Range | Assessment |")
    lines.append("| :--- | :---: | :---: | :--- |")
    
    lines.append(f"| **Start NAV** | `₹{metrics.get('start_nav', 0.0):.4f}` | as of {metrics.get('start_date', 'N/A')} | Period Baseline |")
    lines.append(f"| **Latest / End NAV** | `₹{metrics.get('end_nav', 0.0):.4f}` | as of {metrics.get('end_date', 'N/A')} | Current Valuation |")
    
    ret_val = metrics.get('total_return_pct', 0.0)
    ret_badge = "🟢 Strong Gain" if ret_val > 0 else "🔴 Loss"
    lines.append(f"| **Cumulative Total Return** | `+{ret_val:.2f}%` | Period Growth | {ret_badge} |")

    if metrics.get('cagr_pct') is not None:
        lines.append(f"| **Annualized Return (CAGR)** | `+{metrics.get('cagr_pct'):.2f}%` | Compounded Annual Rate | 🚀 Compounding Pace |")

    lines.append(f"| **Period High NAV** | `₹{metrics.get('period_high_nav', 0.0):.4f}` | on {metrics.get('period_high_date', 'N/A')} | Peak Resistance |")
    lines.append(f"| **Period Low NAV** | `₹{metrics.get('period_low_nav', 0.0):.4f}` | on {metrics.get('period_low_date', 'N/A')} | Trough Support |")
    lines.append(f"| **Maximum Drawdown** | `{metrics.get('max_drawdown_pct', 0.0):.2f}%` | Peak-to-Trough Decline | 🛡️ Downside Volatility |")
    
    if metrics.get('annualized_volatility_pct') is not None:
        lines.append(f"| **Annualized Volatility (σ)** | `{metrics.get('annualized_volatility_pct', 0.0):.2f}%` | Std Deviation of Returns | 📊 Volatility Profile |")

    lines.append("\n---\n")

    # Sample Records Table (Newest 5 and Oldest 5)
    lines.append("## 📋 NAV Time Series Sample")
    lines.append("| Date (DD-MM-YYYY) | Net Asset Value (NAV) | Status / Position |")
    lines.append("| :---: | :---: | :--- |")
    
    # Newest 5
    for item in nav_data[:5]:
        lines.append(f"| `{item['date']}` | **₹{float(item['nav']):.4f}** | 🟢 Recent Session |")

    if len(nav_data) > 10:
        lines.append(f"| *... ({len(nav_data) - 10} intermediate records omitted) ...* | *...* | *...* |")

    # Oldest 5 (if records > 5)
    if len(nav_data) > 5:
        oldest_subset = list(reversed(nav_data[-5:])) if len(nav_data) > 10 else list(reversed(nav_data[5:]))
        for item in reversed(oldest_subset):
            lines.append(f"| `{item['date']}` | ₹{float(item['nav']):.4f} | ⚪ Historical Base |")

    return "\n".join(lines)


def export_to_csv(result: Dict[str, Any], output_path: Path):
    nav_data = result.get("data", [])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "NAV", "Daily_Change_Pct"])
        
        # Sort oldest to newest for daily change
        sorted_records = list(reversed(nav_data))
        prev_val = None
        for item in sorted_records:
            val = float(item["nav"])
            pct_change = round(((val / prev_val) - 1.0) * 100.0, 3) if prev_val else 0.0
            prev_val = val
            writer.writerow([item["date"], val, pct_change])


def generate_interactive_html(result: Dict[str, Any]) -> str:
    meta = result.get("meta", {})
    metrics = result.get("metrics", {})
    horizon = result.get("horizon_label", "Custom Period")
    nav_data = result.get("data", [])

    # Oldest to newest for plotting
    sorted_records = list(reversed(nav_data))
    
    # Decimate if more than 500 records to keep browser smooth
    step = max(1, len(sorted_records) // 400)
    sampled = sorted_records[::step]
    if sorted_records[-1] not in sampled:
        sampled.append(sorted_records[-1])

    dates_json = json.dumps([x["date"] for x in sampled])
    navs_json = json.dumps([float(x["nav"]) for x in sampled])

    name = meta.get("scheme_name", "Mutual Fund")
    code = meta.get("scheme_code", "N/A")
    amc = meta.get("fund_house", "N/A")
    cat = meta.get("scheme_category", "N/A")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NAV History: {name}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #151d30;
      --card-border: #232f48;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-green: #34d399;
      --accent-amber: #fbbf24;
      --accent-rose: #f43f5e;
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
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
    .chart-card {{
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .chart-card h3 {{ font-size: 1.1rem; margin-bottom: 16px; }}
    .chart-container {{ position: relative; height: 420px; width: 100%; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📈 {name}</h1>
      <div class="meta">
        <span>🏛️ <b>Fund House:</b> {amc}</span>
        <span>🏷️ <b>Scheme Code:</b> {code}</span>
        <span>📂 <b>Category:</b> {cat}</span>
        <span>📅 <b>Horizon:</b> {horizon}</span>
      </div>
    </div>

    <div class="grid-kpi">
      <div class="kpi-card">
        <div class="kpi-title">Cumulative Return</div>
        <div class="kpi-value" style="color: var(--accent-green);">+{metrics.get('total_return_pct', 0.0):.2f}%</div>
        <div class="kpi-sub">CAGR: {metrics.get('cagr_pct', 'N/A')}%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Current / Latest NAV</div>
        <div class="kpi-value">₹{metrics.get('end_nav', 0.0):.4f}</div>
        <div class="kpi-sub">as of {metrics.get('end_date', 'N/A')}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Period High / Low</div>
        <div class="kpi-value" style="color: var(--accent-amber);">₹{metrics.get('period_high_nav', 0.0):.2f}</div>
        <div class="kpi-sub">Low: ₹{metrics.get('period_low_nav', 0.0):.2f}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Max Drawdown</div>
        <div class="kpi-value" style="color: var(--accent-rose);">{metrics.get('max_drawdown_pct', 0.0):.2f}%</div>
        <div class="kpi-sub">Volatility: {metrics.get('annualized_volatility_pct', 'N/A')}%</div>
      </div>
    </div>

    <div class="chart-card">
      <h3>📈 Net Asset Value (NAV) Historical Trajectory</h3>
      <div class="chart-container">
        <canvas id="navChart"></canvas>
      </div>
    </div>
  </div>

  <script>
    const ctx = document.getElementById('navChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: {dates_json},
        datasets: [{{
          label: 'NAV (₹)',
          data: {navs_json},
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.12)',
          fill: true,
          tension: 0.2,
          borderWidth: 2,
          pointRadius: 0,
          pointHitRadius: 8
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ labels: {{ color: '#94a3b8' }} }},
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                return ' NAV: ₹' + context.parsed.y.toFixed(4);
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            ticks: {{ color: '#94a3b8', maxTicksLimit: 12 }},
            grid: {{ color: '#232f48' }}
          }},
          y: {{
            ticks: {{ color: '#94a3b8' }},
            grid: {{ color: '#232f48' }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""
    return html

