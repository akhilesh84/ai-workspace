# Mutual Fund Factsheet Analyzer Skill (`mf-factsheet-analyzer`)

A specialized Antigravity skill for comprehensive **36-month historical factsheet and statutory portfolio disclosure analysis** of Indian mutual funds.

## Features
- **Scheme Search & Disambiguation**: Searches `api.mfapi.in` by fund name or code, auto-selects **Direct Plan - Growth**, and interactively resolves ambiguities.
- **Multi-Tier Factsheet Acquisition**: Seamless retrieval across curated local benchmark archives, dynamic AMC statutory portal scrapers (e.g. PPFAS, HDFC MF), and user-provided local disclosure files.
- **SEBI Excel & Disclosure Parser**: Native parsing of statutory `.xlsx` portfolio disclosures, extracting AUM, Portfolio Turnover Ratio (PTR), liquid dry powder, standardized sector weights, and individual security holdings.
- **Dry Powder & Cash Reserves Engine**: Quantifies cash equivalents (TREPS, reverse repo, T-Bills, money market instruments) over 36 months, identifying cash deployment velocity during market pullbacks.
- **Capital Rotation & Turnover**: Evaluates PTR trajectories, holding churn rates, and distinguishes multi-year high-conviction anchors from tactical trades.
- **Sector Drift & Concentration Audit**: Tracks 1M, 3M, 6M, 12M, and 36M sector shifts and computes the Herfindahl-Hirschman Index ($HHI_{sector}$) alongside SEBI 10% single-stock ceiling compliance.
- **Dual Visual Deliverables**: Produces an executive Markdown report and a standalone interactive Chart.js HTML visualization dashboard.

## Directory Structure
```
mf-factsheet-analyzer/
├── v1/
│   ├── SKILL.md                 # Agent skill instructions & workflow
│   ├── README.md                # Skill documentation & CLI guide
│   ├── scripts/
│   │   ├── search_fund.py       # Scheme search & Direct Growth resolver
│   │   ├── parse_portfolio.py   # SEBI standardized XLSX/CSV portfolio parser
│   │   ├── fetch_factsheet.py   # Multi-tier factsheet downloader & cache
│   │   ├── analyze_historical.py# 36-month capital rotation & concentration engine
│   │   └── render_report.py     # Markdown & interactive HTML dashboard generator
│   ├── references/
│   │   ├── amc_sources.json     # AMC statutory portals & pattern rules
│   │   ├── sector_taxonomy.json # Standardized GICS sector mapping
│   │   └── historical_store/    # Pre-indexed 36M historical datasets
│   │       └── 122639_ppfcf.json# Parag Parikh Flexi Cap Fund benchmark dataset
│   └── examples/
│       └── ppfcf_sample_report.md
└── latest -> v1
```

## CLI Usage Examples

```bash
# 1. Search for a fund
python3 skills/mf-factsheet-analyzer/latest/scripts/search_fund.py -q "parag parikh flexi"

# 2. Parse a downloaded SEBI monthly disclosure workbook
python3 skills/mf-factsheet-analyzer/latest/scripts/parse_portfolio.py -f /path/to/portfolio.xlsx

# 3. Analyze 36 months of historical factsheet metrics
python3 skills/mf-factsheet-analyzer/latest/scripts/analyze_historical.py -s 122639

# 4. Generate Markdown & Interactive HTML Reports
python3 skills/mf-factsheet-analyzer/latest/scripts/render_report.py -s 122639 -o /tmp/reports -f both
```

