---
name: mf-factsheet-analyzer
description: >-
  Analyzes historical mutual fund factsheets and SEBI portfolio disclosures across a 36-month horizon.
  Searches schemes via mfapi.in, auto-selects Direct Plan - Growth options (resolving ambiguities interactively),
  acquires statutory disclosures across multiple tiers, and computes deep metrics: capital utilization patterns,
  dry powder & cash reserves, investment rotation & portfolio turnover (PTR), sector allocation drift (1M/3M/6M/12M/36M),
  and sector/stock concentration risk (HHI & SEBI regulatory ceilings).
version: "1.0.0"
---

# Mutual Fund Historical Factsheet Analyzer (v1)

This skill guides the agent in identifying any Indian mutual fund scheme via `api.mfapi.in`, isolating the **Direct Plan - Growth** option, retrieving historical factsheets and statutory monthly disclosures over a **36-month horizon**, and evaluating:
1. **Capital Utilization Patterns**: Equity vs. Debt vs. REITs vs. Cash reserves over 36 months.
2. **Dry Powder & Cash Reserves**: Time series of liquid reserves (TREPS, Reverse Repo, Net Current Assets, T-Bills/Money Market), 36M peak/low/median, and deployment velocity during market pullbacks.
3. **Investment Rotation & Portfolio Turnover**: Historical Portfolio Turnover Ratio (PTR), holding churn, and identification of multi-year core anchor positions vs. tactical trades.
4. **Sector Allocation & Drift**: Multi-period sector drift ($1\text{M} \Delta, 3\text{M} \Delta, 6\text{M} \Delta, 12\text{M} \Delta, 36\text{M} \Delta$) and sector rotation trends.
5. **Concentration Risk Audit**: Sector Herfindahl-Hirschman Index ($HHI_{sector}$), Top 3/5 sector weights, Top 10 stock weights, and compliance against SEBI's 10% single-stock ceiling.

---

## When to Use

Activate this skill when the user asks to:
- Analyze mutual fund factsheets or monthly portfolio disclosures over historical timeframes (e.g., last 36 months).
- Search for a mutual fund or inspect its scheme details (e.g., using `api.mfapi.in/mf/search?q=...`).
- Evaluate how much **cash or dry powder** a mutual fund holds in reserves to deploy into market dips.
- Examine a fund manager's **capital rotation**, **portfolio turnover (PTR)**, or how frequently they buy/sell stocks.
- Inspect **sector allocation shifts**, sector drift over the last few months, or **concentration risk** in top stocks/sectors.

---

## Workflow Steps

### Step 1: Fund Search & Direct-Growth Scheme Resolution

1. Run [`search_fund.py`](./scripts/search_fund.py) passing the fund name or scheme code:
   ```bash
   python3 <path-to-skill>/scripts/search_fund.py --query "<fund name or code>" --json
   ```
   *Example:*
   ```bash
   python3 skills/mf-factsheet-analyzer/latest/scripts/search_fund.py --query "parag parikh flexi" --json
   ```

2. **Handle Resolution State**:
   - **If `status == "RESOLVED"`**: Note the resolved `scheme_code`, `scheme_name`, `fund_house`, `category`, and `isin`. Proceed to Step 2.
   - **If `status == "AMBIGUOUS"`**: 
     - Present the user with the numbered list of matching schemes.
     - Ask the user to confirm their intended option (e.g. via chat prompt or `ask_question`).
     - Once confirmed, run with `--query "<scheme_code>"` to lock the resolution.
   - **If `status == "NOT_FOUND"`**: Inform the user and ask for an alternative fund name or AMC.

---

### Step 2: Factsheet & Historical Portfolio Acquisition

1. Acquire 36-month monthly portfolio disclosures using [`fetch_factsheet.py`](./scripts/fetch_factsheet.py):
   ```bash
   python3 <path-to-skill>/scripts/fetch_factsheet.py --scheme-code <scheme_code>
   ```

2. **Multi-Tier Acquisition Strategy**:
   - **Tier 1 (Curated Store)**: Pre-indexed 36-month historical dataset loaded instantly from `references/historical_store/` (e.g. Parag Parikh Flexi Cap `122639`).
   - **Tier 2 (Live Statutory Portal)**: Dynamically fetches monthly disclosure spreadsheets (`.xlsx`) from the AMC portal (e.g. PPFAS, HDFC MF) and caches them in `~/.cache/mf-factsheets/<scheme_code>/`.
   - **Tier 3 (User Local Files)**: If the user provides a local directory with factsheets, pass `--local-dir /path/to/disclosures/`.
   - **Tier 4 (Daily NAV Stream)**: Pulls up to 750 daily historical NAV records from `api.mfapi.in/mf/<scheme_code>` for return and max drawdown analysis.

---

### Step 3: 36-Month Historical Analytics

1. Execute [`analyze_historical.py`](./scripts/analyze_historical.py) to compute historical analytics:
   ```bash
   python3 <path-to-skill>/scripts/analyze_historical.py --scheme-code <scheme_code> --json
   ```

2. **Extracted Analytical Dimensions**:
   - **Dry Powder Analysis**: Current cash reserve %, 36M historical peak %, low %, median %, and opportunistic deployment velocity events.
   - **Capital Rotation**: Latest PTR %, 36M average PTR %, holding churn rate, and list of 36-month continuous core anchors.
   - **Sector Drift**: Sector weights and multi-period deltas ($1\text{M} \Delta, 3\text{M} \Delta, 12\text{M} \Delta$) labeled as `ACCUMULATING`, `TRIMMING`, or `STABLE`.
   - **Concentration Risk**: Sector HHI ($<1500$ Diversified, $1500-2500$ Moderate, $>2500$ Concentrated), Top 3/5 sector concentration, Top 10 stock weights, and SEBI 10% single-stock ceiling compliance.
   - **NAV Performance**: 36-month total return, 3-year CAGR, and maximum drawdown.

---

### Step 4: Render Reports & Visual Artifacts

1. Run [`render_report.py`](./scripts/render_report.py) to generate both Markdown and interactive HTML outputs:
   ```bash
   python3 <path-to-skill>/scripts/render_report.py --scheme-code <scheme_code> --output-dir /tmp/reports --format both
   ```

2. **Present the Analysis to the User**:
   - Output the structured **Executive Markdown Report** directly in the chat conversation with:
     - KPI Summary table (Dry Powder, PTR, Sector HHI, Top 10 Stocks, 36M Return).
     - Dry Powder & Cash Reserve Dynamics section.
     - Sector Allocation & Historical Drift table.
     - Capital Rotation & Multi-Year Core Holdings table.
     - Concentration Risk Audit & SEBI 10% Cap status.
   - Provide a clickable markdown link to the interactive HTML visualization file (e.g. `file:///tmp/reports/<scheme_code>_factsheet_report.html`) containing the interactive 24-month capital deployment chart and sector allocation visualizer.

---

## Direct CLI Utilities Reference

| Utility | Command Example | Purpose |
| :--- | :--- | :--- |
| **Search & Disambiguate** | `python3 <skill>/scripts/search_fund.py -q "parag parikh flexi"` | Query mfapi.in & filter Direct Growth |
| **Parse SEBI Excel File** | `python3 <skill>/scripts/parse_portfolio.py -f /path/to/sheet.xlsx` | Extract Cash, PTR, Sectors, Holdings |
| **Acquire Disclosures** | `python3 <skill>/scripts/fetch_factsheet.py -s 122639` | Multi-tier factsheet downloader & cache |
| **Historical Analytics** | `python3 <skill>/scripts/analyze_historical.py -s 122639` | 36M capital rotation, dry powder, HHI |
| **Generate Visual Reports**| `python3 <skill>/scripts/render_report.py -s 122639 -f both` | Render Markdown & interactive HTML |

