# Mutual Fund NAV Data Puller Skill (`mf-nav-puller`)

A specialized Antigravity skill for fetching and analyzing daily historical Net Asset Value (NAV) data of Indian mutual funds via the `mfapi.in` Swagger/OpenAPI endpoint (`/mf/{scheme_code}`).

## Features
- **Inception-to-Date Retrieval**: Retrieves complete NAV time-series since scheme inception.
- **Natural Language Horizon Parsing**: Converts queries like `"last 15 months"`, `"3 years"`, `"YTD"`, or explicit dates into ISO 8601 `YYYY-MM-DD` parameters.
- **Typo-Tolerant Scheme Resolution**: Recovers from fund name typos (e.g., `"HDFV midcap"` $\rightarrow$ `"HDFC Mid Cap"`) and auto-selects **Direct Plan - Growth**.
- **Financial Analytics**: Computes Cumulative Return %, CAGR %, Period High & Low NAV, Maximum Drawdown %, and Annualized Volatility %.
- **Multi-Format Exports**: Markdown executive tables, CSV time-series exports, and interactive Chart.js HTML dashboards.

## CLI Usage Examples

```bash
# 1. Pull NAV since inception
python3 skills/mf-nav-puller/latest/scripts/pull_nav.py -q "HDFC midcap fund"

# 2. Pull NAV for the last 15 months
python3 skills/mf-nav-puller/latest/scripts/pull_nav.py -q "parag parikh flexicap" -p "last 15 months"

# 3. Export CSV and interactive HTML chart
python3 skills/mf-nav-puller/latest/scripts/pull_nav.py -q "parag parikh flexicap" -p "last 15 months" -o /tmp/reports --html --csv
```

