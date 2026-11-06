# Kite Portfolio Look-Through Plugin (v3)

A universal, agent-agnostic plugin for analyzing Zerodha Kite and Coin portfolios. It connects via the Model Context Protocol (MCP), extracts holdings and mutual funds, decomposes equity index ETFs (e.g. `NV20`, `NIFTYIETF`, `BANKBEES`, `ITBEES`) and active equity mutual funds into underlying constituent stocks, and automatically synchronizes both ETF benchmark index weights and SEBI monthly mutual fund portfolio disclosures on every run.

---

## What's New in Version 3 (v3)

1. **Automated Mutual Fund Disclosures Synchronization**:
   - Bundles [`update_mf_holdings.py`](./skills/kite-portfolio-lookthrough/v3/scripts/update_mf_holdings.py) to dynamically verify, balance, and refresh mutual fund constituents on every run.
   - Smart monthly TTL logic aligns with SEBI's 10th-of-month disclosure cadence.
2. **Dual-Layer Provenance Tracking**:
   - Reports surface live NSE archive feed timestamps for ETFs and official monthly factsheet disclosure dates for Mutual Funds.
3. **Resilient Offline Execution & Safety Guardrails**:
   - Liquid, overnight, and arbitrage funds are strictly categorized as cash reserves and excluded from equity dilution.
   - Built-in graceful fallbacks ensure reports never fail during network interruptions.

---

## Structure

```
plugins/kite-portfolio-lookthrough/v3/
├── plugin.json
├── AGENT.md
├── system_prompt.md
├── mcp_config.json
├── README.md
└── skills/kite-portfolio-lookthrough/v3/
    ├── SKILL.md
    ├── README.md
    ├── references/
    │   ├── etf_index_constituents.json
    │   └── mf_portfolio_holdings.json
    └── scripts/
        ├── decompose_portfolio.py
        ├── update_constituents.py
        └── update_mf_holdings.py
```
