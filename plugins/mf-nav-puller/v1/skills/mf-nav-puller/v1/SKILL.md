---
name: mf-nav-puller
description: >-
  Pulls historical mutual fund Net Asset Value (NAV) data via the mfapi.in Swagger API endpoint (/mf/{scheme_code}).
  Supports pulling NAV history since fund inception or across specific timeframes (e.g., 'last 15 months', '3 years',
  or ISO 8601 startDate/endDate). Recovers from fund name typos, auto-selects Direct Plan - Growth, and computes
  returns, CAGR, period high/low, and maximum drawdown.
version: "1.0.0"
---

# Mutual Fund NAV Data Puller (v1)

This skill guides the agent in pulling and analyzing historical mutual fund Net Asset Value (NAV) data via the Swagger/OpenAPI endpoint on `mfapi.in` (`GET /mf/{scheme_code}`).

---

## When to Use

Activate this skill when the user asks to:
- Pull NAV data of any mutual fund (e.g. *"Pull the NAV of HDFC Mid Cap Fund"*).
- Retrieve full NAV history since inception (e.g. *"Pull NAV since inception"*).
- Fetch NAV data for a relative timeframe (e.g. *"Pull NAV data of Parag Parikh Flexi Cap Fund for the last 15 months"*).
- Check historical performance, CAGR, period peak/troughs, or drawdowns from daily NAV prices.
- Export NAV series into CSV or view interactive NAV chart visualizers.

---

## Workflow Steps

### Step 1: Fund Scheme Resolution & Typo Recovery

1. Run [`resolve_scheme.py`](./scripts/resolve_scheme.py) to resolve the fund query:
   ```bash
   python3 <path-to-skill>/scripts/resolve_scheme.py --query "<fund name or code>" --json
   ```
   *Handles typos automatically (e.g., `"HDFV midcap"` $\rightarrow$ `"HDFC Mid Cap"`).*

2. **Handle Resolution State**:
   - **`status == "RESOLVED"`**: Note the `scheme_code` and proceed to Step 2.
   - **`status == "AMBIGUOUS"`**: Present candidate options to the user and prompt them to confirm or pass `--select <N>`.
   - **`status == "NOT_FOUND"`**: Inform the user and ask for an alternative fund name or code.

---

### Step 2: Date Range Parsing

Determine the target horizon:
- **Since Inception / All Time**: Omit `startDate` and `endDate` query parameters.
- **Relative Horizon (e.g. "last 15 months", "3 years", "YTD")**: Use [`date_parser.py`](./scripts/date_parser.py) to automatically compute `startDate` and `endDate` in ISO 8601 (`YYYY-MM-DD`).
- **Explicit Dates**: Format as `YYYY-MM-DD`.

---

### Step 3: Fetch & Analyze NAV Data

1. Run [`pull_nav.py`](./scripts/pull_nav.py) with the resolved query and period:
   ```bash
   # Example 1: Since Inception
   python3 <path-to-skill>/scripts/pull_nav.py --query "HDFC midcap fund"

   # Example 2: Last 15 Months
   python3 <path-to-skill>/scripts/pull_nav.py --query "parag parikh flexicap" --period "last 15 months"

   # Example 3: With CSV and HTML Exports
   python3 <path-to-skill>/scripts/pull_nav.py --query "parag parikh flexicap" --period "last 15 months" --output-dir /tmp/nav_reports
   ```

2. **Extracted Metrics**:
   - **Start NAV & End NAV** (with session dates)
   - **Cumulative Total Return %** and **Annualized CAGR %**
   - **Period High & Low NAV** (with calendar dates)
   - **Maximum Drawdown %** (peak-to-trough decline)
   - **Annualized Volatility %** (standard deviation $\times \sqrt{250}$)

---

### Step 4: Present the Results

1. Output the structured Markdown performance table in the conversation:
   - Executive KPI table (Start/End NAV, Total Return %, CAGR %, Period High/Low, Max DD, Volatility).
   - Sample time series records (newest 5 and oldest 5 sessions).
2. If exports were generated (CSV or interactive HTML), provide clickable markdown links:
   - `file:///path/to/<scheme_code>_nav_chart.html`
   - `file:///path/to/<scheme_code>_nav_history.csv`

---

## Direct CLI Utilities Reference

| Utility | Command Example | Purpose |
| :--- | :--- | :--- |
| **Resolve Scheme** | `python3 <skill>/scripts/resolve_scheme.py -q "HDFV midcap"` | Fuzzy search with typo recovery |
| **Parse Dates** | `python3 <skill>/scripts/date_parser.py -p "last 15 months"` | Convert expression to ISO 8601 |
| **Pull NAV (Inception)** | `python3 <skill>/scripts/pull_nav.py -q "HDFC midcap"` | Full NAV history since inception |
| **Pull NAV (Range)** | `python3 <skill>/scripts/pull_nav.py -q "parag parikh flexi" -p "15m"` | Range fetch with startDate/endDate |

