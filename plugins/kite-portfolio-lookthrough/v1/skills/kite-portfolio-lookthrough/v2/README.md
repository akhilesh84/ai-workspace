# Kite Portfolio Look-Through Skill (v2)

Comprehensive look-through portfolio decomposition and asset allocation skill for Zerodha Kite and Coin portfolios.

## What's New in v2

1. **Explicit Demat + ETF Scoping (Step 4)**: The consolidated stock analysis explicitly indicates it covers direct Demat stock holdings plus decomposed equity ETF positions (NV20, NIFTYIETF, BANKBEES, etc.).
2. **Mutual Fund Portfolio Breakdown (Step 5)**: Pulls mutual fund holdings via `get_mf_holdings`, presenting units, average NAV, current NAV, invested vs current value, returns, and AMC concentration.
3. **Unified Multi-Layer Equity Look-Through (Step 6)**: Aggregates equity exposure across:
   - Direct Demat stocks
   - Decomposed Demat equity ETFs
   - Active equity mutual funds (Parag Parikh Flexi Cap, HDFC Mid-Cap, PP ELSS, ICICI Aggressive Hybrid)
   - Excludes Liquid and Arbitrage funds (tracked as cash/liquidity buffer).
4. **Enhanced CLI Tool**: `decompose_portfolio.py` supports `--mf-file <path_to_mf_json>` to generate all three sections deterministically in markdown or JSON.

## Usage

```bash
# Demat & ETF look-through only
python3 scripts/decompose_portfolio.py holdings.json

# Unified look-through including Mutual Funds
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json

# Raw JSON output
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json --json
```
