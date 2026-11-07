# Mutual Fund Returns Comparator Plugin (v1)

A plugin for Google Antigravity and agentic workflows that compares historical performance, volatility, and risk metrics across two or more mutual funds.

## Features

- **Automated Scheme Resolution & Typo Recovery**: Automatically resolves fund names to verified AMFI codes and filters for **Direct Plan - Growth**.
- **Trading Session Alignment**: Harmonizes mismatched trading calendars and holidays into a unified dataset.
- **Normalized Growth Index**: Rebases all funds to ₹100 on the starting session for intuitive visual comparison.
- **Multi-Factor Risk Analytics**: Evaluates CAGR, Total Return, Maximum Drawdown, Annualized Volatility, and Sharpe Ratio ($R_f = 6.5\%$).
- **Multi-Format Exports**: Outputs side-by-side Markdown comparison tables, synchronized CSV time series, and standalone interactive HTML Chart.js dashboards.

## Dependencies

- Requires the **`mf-nav-puller`** skill to retrieve daily NAV records from `https://api.mfapi.in`.

## Usage

```bash
python3 plugins/mf-returns-comparator/v1/skills/mf-returns-comparator/v1/scripts/compare_funds.py \
  --funds "DSP flexicap" "Parag Parikh flexicap" "HDFC flexicap" \
  --period "last 5 years" \
  --output-dir reports/flexicap_comparison
```

