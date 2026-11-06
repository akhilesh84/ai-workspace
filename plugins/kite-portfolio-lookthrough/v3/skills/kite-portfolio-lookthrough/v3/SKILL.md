---
name: kite-portfolio-lookthrough
description: >-
  Analyzes Zerodha Kite portfolios by fetching stock & ETF holdings and mutual funds, decomposing equity
  index ETFs (NV20, NIFTYIETF, BANKBEES) and active equity mutual funds into underlying constituent stocks
  to uncover true look-through equity exposure and sector allocation across Demat and Mutual Funds.
  Preserves commodity ETFs (GOLDIETF, SILVERBEES), excludes liquid/arbitrage funds from equity look-through,
  and dynamically synchronizes ETF benchmark weights and Mutual Fund monthly disclosures on every run.
---

# Kite Portfolio Look-Through Analysis (v3)

This skill guides the agent in pulling a user's Zerodha Kite stock portfolio and Mutual Fund holdings, verifying authentication, decomposing equity index ETFs and active equity mutual funds into their underlying constituent stocks, and calculating true look-through equity holdings and sector weightages across Demat and Mutual Funds.

**What's new in v3:**
- **Automated Mutual Fund Disclosures Synchronization**: Automatically verifies and syncs mutual fund portfolio constituents on every run via [`update_mf_holdings.py`](./scripts/update_mf_holdings.py).
- **Dual-Layer Provenance Tracking**: Tracks and surfaces official factsheet dates (e.g., SEBI monthly disclosures) alongside live NSE index archive feeds.
- **Smart Staleness Detection & Guardrails**: Auto-classifies liquid and arbitrage funds into cash reserves, and balances long-tail weights with zero report disruption.

---

## Workflow Steps

### Step 1: Verify Kite Authentication

1. Attempt to call `get_profile` via the `kite` MCP (Model Context Protocol) server:
   - Tool: `get_profile`
   - Parameters: `{}`
2. **If authenticated**: Proceed directly to Step 2.
3. **If not authenticated** (e.g., error indicates session expired or "Please log in first"):
   - Call the `login` tool from the `kite` MCP server.
   - Display the mandatory risk warning to the user:
     > ⚠️ **WARNING: AI systems are unpredictable and non-deterministic. By continuing, you agree to interact with your Zerodha account via AI at your own risk.**
   - Present the authorization URL returned by the `login` tool as a clickable markdown link.
   - Instruct the user to complete the login in their browser and confirm once done.
   - Wait for the user's confirmation before calling `get_profile` again.

---

### Step 2: Retrieve Demat Portfolio Holdings

1. Call `get_holdings` from the `kite` MCP server:
   - Tool: `get_holdings`
   - Parameters: `{}`
2. Save the returned JSON holdings data for Step 4 and Step 6.

---

### Step 3: Retrieve Mutual Fund Portfolio Holdings

1. Call `get_mf_holdings` from the `kite` MCP server:
   - Tool: `get_mf_holdings`
   - Parameters: `{}`
2. Save the returned JSON mutual fund holdings data for Step 5 and Step 6.

---

### Step 4: Present Demat & ETF Consolidated Look-Through Analysis

> [!IMPORTANT]
> **Explicit Scope**: This section presents the consolidated look-through analysis of **Direct Demat Stock Holdings + Decomposed Equity ETF Holdings** (e.g. `NV20`, `NIFTYIETF`, `BANKBEES`).

1. Use the bundled helper script [`decompose_portfolio.py`](./scripts/decompose_portfolio.py):
   ```bash
   python3 <path-to-skill>/scripts/decompose_portfolio.py <path_to_demat_holdings_json>
   ```
   *Note: Automatically syncs live exchange feeds (NSE archives) via [`update_constituents.py`](./scripts/update_constituents.py) to reflect dynamic index weights.*
2. **Decomposition Rules**:
   - **Equity Index ETFs** (e.g., `NV20`, `NIFTYIETF`, `NIFTYBEES`, `BANKBEES`): Replaced proportionally by constituent stocks according to live index weights loaded from [`references/etf_index_constituents.json`](./references/etf_index_constituents.json).
   - **Commodity ETFs** (e.g., `GOLDIETF`, `SILVERBEES`): **Preserved as-is** (not decomposed into equity constituents).
   - **Direct Stocks**: Combined with look-through weights from decomposed ETFs.
3. **Present the Formatted Demat & ETF Report**:
   - **Demat Portfolio Summary**: Total Demat portfolio value, direct equity total, decomposed ETF total, preserved commodity ETFs.
   - **Demat & ETF Look-Through Sector Allocation**: Sector weightages across direct Demat stocks and decomposed ETF constituents.
   - **Consolidated Demat & ETF Stock Holdings Table**:
     - Stock Symbol
     - Direct Demat Holding Value (₹)
     - Value via each decomposed ETF (₹)
     - Total Effective Value (₹)
     - Effective Demat Portfolio Weight (%)
   - **Commodity Holdings (As-Is)**: Gold and Silver ETFs with units, purchase price, LTP, current value, and unrealized P&L.
   - **ETF to Benchmark Index Mapping (Legends Table)**: ETF symbol, scheme name, benchmark tracked, category, and look-through treatment.

---

### Step 5: Present Mutual Funds Portfolio

Present a dedicated, structured breakdown of the user's mutual fund holdings:
1. **Executive Snapshot**:
   - Total MF Invested Capital (₹)
   - Total Current Valuation (₹)
   - Total Unrealized Profit / Loss (₹)
   - Overall Absolute Return (%)
   - **Constituents Synchronization Status**: Live synced / Verified up-to-date with SEBI monthly disclosures.
2. **Mutual Fund Scheme Holdings Table**:
   - Scheme / Fund Name (Direct - Growth)
   - Folio Number
   - Units Held
   - Average Purchase NAV (₹)
   - Current Market NAV (₹)
   - Invested Capital (₹)
   - Current Value (₹)
   - Unrealized P&L (₹) & Return (%)
   - Portfolio Weight (%)
3. **Asset Class & Category Breakdown**:
   - **Pure Equity Funds**: Flexi Cap, Mid Cap, Large Cap, ELSS (Tax Saver).
   - **Hybrid Funds**: Aggressive Hybrid, Balanced Advantage.
   - **Liquid & Cash Management Funds**: Excluded from equity look-through and tracked as cash buffer / liquidity reserve.
4. **Fund House (AMC) Concentration**: Allocation distribution across AMCs (e.g. PPFAS, HDFC, ICICI Prudential).

---

### Step 6: Unified Multi-Layer Equity Look-Through Analysis (Demat + ETFs + Mutual Funds)

Unpack and merge all equity holdings across direct Demat stocks, index ETFs, and active equity mutual funds into a single master equity exposure view:

1. **Exclusion and Filtering Rules**:
   - **EXCLUDE**: Liquid funds (e.g., Parag Parikh Liquid, ICICI Liquid), Overnight funds, Arbitrage funds, and pure debt/cash equivalents. These represent dry powder and must not dilute true equity exposure.
   - **INCLUDE**: Direct Demat equities, Demat equity ETFs (decomposed), pure equity mutual funds (decomposed), and the equity sleeve of aggressive hybrid funds (~70% decomposed).
2. **Execute Unified Decomposition with Automated Mutual Fund Sync**:
   ```bash
   python3 <path-to-skill>/scripts/decompose_portfolio.py <path_to_demat_json> --mf-file <path_to_mf_json>
   ```
   *Optional Flags:*
   - `--skip-mf-sync`: Skip online refresh and use local cache only (instant offline mode).
   - `--force-mf-sync`: Force fresh re-fetch of disclosures regardless of cache TTL.
3. **Present Unified Multi-Layer Analysis**:
   - **Master Asset Allocation**: Direct Equities & ETFs vs. Active MF Equity Sleeve vs. Liquid/Cash Reserves vs. Commodities.
   - **Consolidated Master Equity Holdings Table (≥0.50% weight)**:
     - Stock Symbol / Company Name
     - Direct Demat Value (₹)
     - Value via ETFs (₹)
     - Value via Mutual Funds (₹)
     - Total Combined Effective Value (₹)
     - Effective Share of Total Working Equity (%)
   - **Unified Look-Through Sector Allocation**: Real aggregate sector exposures across all three layers (e.g., Financial Services, Power, Energy, FMCG, Tech).
   - **Compounding Overlap & Strategic Insights**:
     - **Hidden Compounding Concentration**: Explicitly highlight where direct stock holdings overlap with mutual fund core holdings (e.g., HDFC Bank, Power Grid, ITC, Coal India, Kotak Mahindra Bank).
     - **Unique Holdings via Funds**: Highlight exposure gained exclusively via ETFs or Mutual Funds (e.g., Reliance Industries, US AI/Cloud tech like Alphabet and Microsoft, mid-caps).
     - **Cash Cushion & Liquidity**: Quantify liquid reserve dry powder ready for systematic deployment or market corrections.
