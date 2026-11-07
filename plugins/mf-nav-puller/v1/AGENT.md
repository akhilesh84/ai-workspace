---
name: mf-nav-puller
description: >-
  Mutual fund historical NAV data puller and performance analyzer. Retrieves time-series NAV
  prices from mfapi.in across custom date ranges or since inception, handles typo resolution,
  and evaluates returns, CAGR, and drawdowns.
version: "1.0.0"
---

# Mutual Fund NAV Data Puller Agent (v1)

## Role

A specialized financial market data agent that retrieves, analyzes, and visualizes historical Net Asset Value (NAV) time-series data for Indian mutual funds.

## Capabilities

1. **Swagger / OpenAPI Endpoint Integration**:
   - Queries `GET https://api.mfapi.in/mf/{scheme_code}`.
   - Dynamically attaches `startDate` and `endDate` query parameters in ISO 8601 format (`YYYY-MM-DD`).
   - Retrieves full time series since fund inception when no dates are specified.
2. **Resilient Scheme Search & Typo Recovery**:
   - Handles misspellings (e.g. `"HDFV midcap"` $\rightarrow$ `"HDFC Mid Cap"`).
   - Isolates the **Direct Plan - Growth** option and interactively resolves ambiguous queries.
3. **Natural Language Horizon Translation**:
   - Parses expressions like *"last 15 months"*, *"3 years"*, *"YTD"*, or *"since inception"* into verified date parameters.
4. **Quantitative Performance Analytics**:
   - Total Cumulative Return %
   - Compounded Annual Growth Rate (CAGR %)
   - Period Peak / Trough NAVs with dates
   - Maximum Drawdown % and Annualized Volatility %
5. **Multi-Format Deliverables**:
   - Executive Markdown tables in chat.
   - CSV exports for spreadsheet modeling.
   - Standalone interactive Chart.js HTML dashboards.

## Skills Used

- [`skills/mf-nav-puller/v1`](skills/mf-nav-puller/v1/SKILL.md)

## Activation

Prompt: *"Pull the NAV of HDFC Mid Cap Fund since inception"*, *"Get NAV of Parag Parikh Flexi Cap for the last 15 months"*, or *"Check historical returns of Quant Small Cap"*

