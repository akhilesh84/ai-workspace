# Mutual Fund NAV Data Puller Plugin (v1)

A universal plugin for pulling and analyzing Indian mutual fund historical Net Asset Value (NAV) data via the mfapi.in Swagger/OpenAPI endpoint (`/mf/{scheme_code}`).

## Features
- **Inception-to-Date & Range Queries**: Full time series since inception or bounded by ISO 8601 start/end dates.
- **Natural Language Parsing**: Automatic translation of `"last 15 months"`, `"3 years"`, `"since inception"`, etc.
- **Typo Tolerance**: Fuzzy recovery of misspellings in fund names (e.g. `"HDFV midcap"`).
- **Performance Analytics**: Computes Return %, CAGR %, Period High/Low, Max Drawdown %, and Volatility %.
- **Multi-Output Format**: Markdown reports, CSV data exports, and interactive Chart.js HTML dashboards.

## Structure
```
plugins/mf-nav-puller/v1/
├── plugin.json
├── AGENT.md
├── system_prompt.md
├── mcp_config.json
├── README.md
└── skills/mf-nav-puller/v1/
    ├── SKILL.md
    ├── README.md
    ├── scripts/
    │   ├── pull_nav.py
    │   ├── resolve_scheme.py
    │   ├── date_parser.py
    │   └── render_nav_report.py
    └── examples/
        ├── hdfc_midcap_inception.md
        └── ppfcf_15m_nav.md
```

