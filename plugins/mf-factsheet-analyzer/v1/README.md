# Mutual Fund Historical Factsheet Analyzer Plugin (v1)

A universal plugin for analyzing 36-month historical factsheets and statutory SEBI portfolio disclosures of Indian mutual funds.

## Features

1. **Automated Fund Search & Disambiguation**:
   - Queries `api.mfapi.in/mf/search`.
   - Filters for **Direct Plan - Growth** schemes.
   - Surfaces multiple options when ambiguous for interactive selection.

2. **Multi-Tier Factsheet Acquisition**:
   - Pre-indexed benchmark repository for flagship schemes (e.g. Parag Parikh Flexi Cap `122639`).
   - Live AMC statutory disclosure scrapers for downloading monthly `.xlsx` reports into `~/.cache/mf-factsheets/<scheme_code>/`.
   - Support for custom local disclosure directories.

3. **SEBI Portfolio Disclosure Parsing**:
   - Native parsing of Excel workbooks using `openpyxl`.
   - Extracts AUM, Portfolio Turnover Ratio (PTR), Dry Powder (Cash, TREPS, Reverse Repo, Money Market), normalized sector weights, and stock holdings.

4. **36-Month Historical Analytics**:
   - Capital utilization patterns over time.
   - Dry powder cash reserve statistics (range, median, deployment velocity).
   - Capital rotation speed, holding churn, and identification of 36-month core anchors.
   - Multi-period sector drift (1M, 3M, 6M, 12M, 36M deltas) and trend classification.
   - Concentration risk audit: Sector HHI, Top 10 stocks, and SEBI 10% single-stock ceiling compliance.

5. **Dual Visual Reporting**:
   - Executive Markdown report with KPI cards and tables.
   - Interactive standalone HTML report widget (`report.html`) powered by Chart.js.

## Directory Structure

```
plugins/mf-factsheet-analyzer/v1/
├── plugin.json
├── AGENT.md
├── system_prompt.md
├── mcp_config.json
├── README.md
└── skills/mf-factsheet-analyzer/v1/
    ├── SKILL.md
    ├── README.md
    ├── references/
    │   ├── amc_sources.json
    │   ├── sector_taxonomy.json
    │   └── historical_store/
    │       └── 122639_ppfcf.json
    ├── scripts/
    │   ├── search_fund.py
    │   ├── parse_portfolio.py
    │   ├── fetch_factsheet.py
    │   ├── analyze_historical.py
    │   └── render_report.py
    └── examples/
        └── ppfcf_sample_report.md
```

