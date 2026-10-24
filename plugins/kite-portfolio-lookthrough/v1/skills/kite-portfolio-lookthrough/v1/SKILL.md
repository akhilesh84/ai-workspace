---
name: kite-portfolio-lookthrough
description: >-
  Analyzes Zerodha Kite portfolios by fetching holdings and decomposing equity index ETFs
  (such as NV20, NIFTYIETF, BANKBEES, etc.) into their constituent stocks based on index weightages
  to uncover true look-through equity exposure and sector allocation. Handles Kite authentication
  and preserves commodity ETFs (e.g. GOLDIETF, SILVERBEES) as-is.
---

# Kite Portfolio Look-Through Analysis

This skill guides the agent in pulling a user's Zerodha Kite stock portfolio, verifying authentication, decomposing equity index ETFs into their underlying constituent stocks, and calculating true look-through equity holdings and sector weightages.

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

### Step 2: Retrieve Portfolio Holdings

1. Call `get_holdings` from the `kite` MCP server:
   - Tool: `get_holdings`
   - Parameters: `{}`
2. Save or pipe the returned JSON holdings data into Step 3.

---

### Step 3: Decompose Equity ETFs (Look-Through)

1. Use the bundled helper script [`decompose_portfolio.py`](./scripts/decompose_portfolio.py):
   ```bash
   python3 ./scripts/decompose_portfolio.py <path_to_holdings_json>
   # or
   python3 <path-to-skill>/scripts/decompose_portfolio.py <path_to_holdings_json>
   ```
   *Note: On every run, the script automatically queries the live exchange feeds (NSE archives) via [`update_constituents.py`](./scripts/update_constituents.py) to detect index rebalances, verify constituent freshness, and adjust for price movements, eliminating the risk of using stale index weights.*
2. **Decomposition Rules**:
   - **Equity Index ETFs** (e.g., `NV20`, `NIFTYIETF`, `NIFTYBEES`, `BANKBEES`, `ITBEES`): Replaced proportionally by their constituent stocks according to the underlying benchmark index weights loaded and dynamically refreshed from [`references/etf_index_constituents.json`](./references/etf_index_constituents.json).
   - **Commodity ETFs** (e.g., `GOLDIETF`, `GOLDBEES`, `SILVERIETF`, `SILVERBEES`): **Must not** be decomposed into equity constituents. They are preserved and represented as commodity assets as-is.
   - **Direct Stocks**: Combined with the look-through weights from the decomposed ETFs to show the true effective value and percentage weight for each company in the overall equity portfolio.

---

### Step 4: Present the Consolidated Analysis

Present a comprehensive, formatted markdown report with:
1. **Portfolio Summary**: Total portfolio value, list of decomposed equity ETFs, and preserved commodity ETFs.
2. **True Look-Through Sector Allocation**: Sector weightages calculated across both direct stocks and ETF constituent look-throughs.
3. **Consolidated Stock Holdings Table**:
   - Stock Symbol
   - Direct Holding Value (₹)
   - Value via each decomposed ETF (₹)
   - Total Effective Value (₹)
   - Effective Portfolio Weight (%)
4. **Commodity Holdings (As-Is)**: Gold and Silver ETFs separated with quantity, average price, LTP, current value, and P&L.
5. **ETF to Benchmark Index Mapping (Legends Table)**:
   - ETF Ticker Symbol (e.g., `NV20`, `NIFTYIETF`, `GOLDIETF`)
   - Official Fund / Scheme Name
   - Benchmark Index or Underlying Asset Tracked (e.g., `Nifty 50 Value 20 Index`, `Nifty 50 Index`, `Domestic Physical Gold Spot`)
   - Asset Category & Classification
   - Value in Portfolio (₹)
   - Treatment in Analysis (Decomposed vs. Preserved as-is)
6. **Key Strategic Insights**: Highlighting hidden concentration, top overweight/underweight sectors, and significant differences between direct demat holdings and true look-through exposure.
