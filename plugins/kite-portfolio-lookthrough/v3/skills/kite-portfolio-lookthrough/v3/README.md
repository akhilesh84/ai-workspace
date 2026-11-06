# Kite Portfolio Look-Through Skill (v3)

Comprehensive look-through portfolio decomposition and asset allocation skill for Zerodha Kite and Coin portfolios.

## What's New in v3

1. **Automated Dynamic Mutual Fund Disclosures Synchronization**:
   - Integrates `update_mf_holdings.py` to auto-discover active Coin mutual funds and synchronize constituent disclosures on every report run.
   - Smart monthly TTL check respects SEBI's 10th-of-month portfolio disclosure timeline.
2. **Dual-Layer Provenance Tracking**:
   - Explicitly displays ETF index weights provenance (live NSE exchange feeds) and Mutual Fund factsheet provenance (SEBI monthly disclosures) in both CLI and markdown reports.
3. **Resilient Offline Execution**:
   - Added `--skip-mf-sync` and `--force-mf-sync` CLI flags to give full control over network calls versus instant cached executions.
4. **Liquid & Cash Reserve Guarantee**:
   - Automated categorization rules ensure liquid, overnight, and arbitrage mutual funds remain isolated as cash equivalents.

## Usage

```bash
# Demat & ETF look-through only
python3 scripts/decompose_portfolio.py holdings.json

# Unified look-through with automated Mutual Fund disclosure sync
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json

# Force fresh disclosure re-fetch
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json --force-mf-sync

# Offline fast mode (skip online sync)
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json --skip-mf-sync --skip-live-sync

# Raw JSON output
python3 scripts/decompose_portfolio.py holdings.json --mf-file mf_holdings.json --json
```
