---
name: mf-returns-comparator
description: >-
  Compares historical Net Asset Value (NAV) returns, compounded annual growth rates (CAGR),
  maximum drawdowns, annualized volatilities, and Sharpe ratios across two or more mutual funds
  over specified horizons (e.g., 'last 3 years', '5 years', or ISO 8601 dates). Depends on and
  utilizes the mf-nav-puller skill to resolve schemes, fetch historical NAV series, align trading sessions,
  rebase series to base 100, and generate comparative Markdown matrices, CSV datasets, and interactive
  multi-line Chart.js overlay dashboards.
version: "1.0.0"
---

# Mutual Fund Returns & Risk Comparator Skill (v1)

This skill provides comparative quantitative analysis across two or more Indian mutual funds over matching time horizons. It leverages the **`mf-nav-puller`** skill to resolve schemes, retrieve time-series NAV records, synchronize trading dates, and generate side-by-side performance matrices and interactive visualizers.

---

## When to Use

Activate this skill whenever the user asks to:
- Compare returns or performance between two or more mutual funds (e.g. *"Compare DSP Flexi Cap and Parag Parikh Flexi Cap over the last 3 years"*).
- Evaluate peer funds within a category on risk-adjusted metrics (CAGR, Max Drawdown, Volatility $\sigma$, Sharpe Ratio).
- Rebase multiple funds to 100 on a common date for visual growth trajectory comparison.
- Generate comparative multi-fund CSV datasets or interactive Chart.js overlay charts.

---

## Architecture & Dependency on `mf-nav-puller`

This skill builds upon **`mf-nav-puller`** as its data engine:
1. **Scheme Resolution**: Uses `resolve_scheme.py` from `mf-nav-puller` to auto-resolve Direct Plan - Growth options and handle user typos.
2. **NAV Time-Series Extraction**: Uses `pull_nav.py` / `fetch_nav_data` from `mf-nav-puller` to query `https://api.mfapi.in/mf/{scheme_code}` with ISO 8601 date ranges.
3. **Session Alignment & Rebasing**: Synchronizes common market trading days across all funds and rebases their initial values to 100.
4. **Comparative Risk Analytics**: Computes side-by-side Total Return, CAGR, Max Drawdown, Annualized Volatility, and Sharpe Ratio ($R_f = 6.5\%$).

```
┌──────────────────────────────────────────────────────────┐
│                mf-returns-comparator                     │
│  (Session Alignment • Base 100 Rebasing • Risk Matrix)   │
└───────────────────────────┬──────────────────────────────┘
                            │ depends on / utilizes
┌───────────────────────────▼──────────────────────────────┐
│                    mf-nav-puller                         │
│  (resolve_scheme • date_parser • api.mfapi.in fetcher)  │
└──────────────────────────────────────────────────────────┘
```

---

## Workflow Steps

### Step 1: Execute Comparison CLI

Run [`compare_funds.py`](./scripts/compare_funds.py) passing the list of fund names or codes:

```bash
# Example 1: Comparing 3 funds over last 5 years
python3 <path-to-skill>/scripts/compare_funds.py \
  --funds "DSP flexicap" "Parag Parikh flexicap" "HDFC flexicap" \
  --period "last 5 years" \
  --output-dir reports/flexicap_comparison

# Example 2: Comparing 2 funds over last 3 years with JSON output
python3 <path-to-skill>/scripts/compare_funds.py \
  --funds "Quant Small Cap" "Nippon India Small Cap" \
  --period "last 3 years" \
  --json
```

### Step 2: Metrics Generated

For each fund over the synchronized market sessions:
- **Initial NAV & Latest NAV**
- **Cumulative Total Return %**: Period growth
- **Annualized Return (CAGR %)**: Compounded annual compounding pace
- **Maximum Drawdown (MaxDD %)**: Peak-to-trough decline
- **Annualized Volatility ($\sigma$ %)**: 252-day basis standard deviation
- **Sharpe Ratio**: Risk-adjusted excess return over $R_f = 6.5\%$
- **Period High & Low NAV**: Peak and trough price points with calendar dates

### Step 3: Present Deliverables

1. **Structured Side-by-Side Markdown Matrix**: Display the comparative performance table in chat.
2. **Key Qualitative Insights**: Highlight the return leader, the downside protector, and the risk-adjusted winner.
3. **Clickable Artifact Links**: Provide clickable file links using `file://` scheme to:
   - `file:///path/to/nav_comparison.html` (interactive Chart.js overlay)
   - `file:///path/to/nav_comparison.csv` (synchronized daily CSV)

---

## Direct CLI Reference

| Flag / Option | Description | Example |
| :--- | :--- | :--- |
| `--funds`, `-f` | List of fund names or scheme codes (required) | `--funds "DSP flexicap" "HDFC flexicap"` |
| `--period`, `-p` | Time horizon expression | `--period "last 3 years"`, `"since inception"` |
| `--start-date` | Explicit ISO start date | `--start-date 2021-01-01` |
| `--end-date` | Explicit ISO end date | `--end-date 2024-01-01` |
| `--output-dir`, `-o` | Output directory for artifacts | `--output-dir reports/comparison` |
| `--csv` | Custom CSV destination path | `--csv /tmp/comp.csv` |
| `--html` | Custom HTML destination path | `--html /tmp/comp.html` |
| `--json` | Emit structured JSON summary | `--json` |

