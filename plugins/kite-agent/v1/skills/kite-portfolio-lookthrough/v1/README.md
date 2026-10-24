# Kite Portfolio Look-Through Analysis

An **agent-agnostic, open-standard** skill and toolset for analyzing Zerodha Kite stock portfolios. It automatically fetches demat holdings via the standard Model Context Protocol (MCP) Kite server, decomposes equity index ETFs (such as `NV20`, `NIFTYIETF`, `NIFTYBEES`, `BANKBEES`, etc.) into their underlying constituent stocks based on index weightages, and reveals the user's true "look-through" equity and sector exposure while preserving commodity ETFs (such as `GOLDIETF` and `SILVERBEES`) as-is.

---

## 🏗️ Architecture & Decoupled Design

This skill is designed without proprietary coupling to any single AI assistant:
1. **Tool Interface:** Uses the open **Model Context Protocol (MCP)** (`kite` server: `get_profile`, `login`, `get_holdings`).
2. **Business Logic:** Pure Python 3 standard library script (`scripts/decompose_portfolio.py`), requiring **zero third-party dependencies**.
3. **Data & Weights:** Plain JSON reference file (`references/etf_index_constituents.json`) containing index constituents, weights, sector mappings, and commodity filters.
4. **Agent Instructions:** Standard Markdown workflow file (`SKILL.md`) compatible with Claude, GitHub Copilot, Antigravity, or Cursor.

---

## 🔌 Universal Agent Setup

### 1. Google Antigravity (IDE / CLI)
- **Global:** Keep this folder at `~/.gemini/config/skills/kite-portfolio-lookthrough/`.
- **Project/Repo:** Place in `.agents/skills/kite-portfolio-lookthrough/`.
- **Usage:** Run `/kite-portfolio-lookthrough` in chat or `agy -i "/kite-portfolio-lookthrough"`.

---

### 2. Anthropic Claude (Claude Desktop & Claude Code)
1. **Configure MCP:** Add the Kite MCP server to your `claude_desktop_config.json` (or Claude Code MCP config):
   ```json
   {
     "mcpServers": {
       "kite": {
         "command": "node",
         "args": ["<path-to-kite-mcp-bundle>"]
       }
     }
   }
   ```
2. **Add to Instructions:** Reference `SKILL.md` in your project's `CLAUDE.md`:
   ```markdown
   When asked to analyze Zerodha portfolio or uncover ETF look-through exposure,
   follow the instructions in `kite-portfolio-lookthrough/SKILL.md`.
   ```
3. **Usage:** Prompt Claude: *"Analyze my Kite portfolio look-through"*.

---

### 3. GitHub Copilot (VS Code / Copilot Agent Mode)
1. Ensure the Kite MCP server is active in VS Code.
2. In `.github/copilot-instructions.md`, add:
   ```markdown
   When analyzing Kite portfolios or ETF holdings, follow `kite-portfolio-lookthrough/SKILL.md`
   and run `python3 kite-portfolio-lookthrough/scripts/decompose_portfolio.py`.
   ```
3. **Usage:** Prompt Copilot: *"Check my Kite portfolio and decompose ETFs to show true sector exposure"*.

---

### 4. Standalone CLI (No AI Required)
You can also run the look-through engine directly from the command line:

```bash
# From a saved Kite holdings JSON file:
python3 scripts/decompose_portfolio.py holdings.json

# Or piping directly from standard input:
cat holdings.json | python3 scripts/decompose_portfolio.py

# Or get raw JSON output for downstream tools:
python3 scripts/decompose_portfolio.py holdings.json --json
```

---

## 📁 Repository Layout

```text
kite-portfolio-lookthrough/
├── README.md                              # Multi-agent setup & usage guide
├── SKILL.md                               # Universal agent workflow instructions
├── scripts/
│   └── decompose_portfolio.py             # Pure Python 3 decomposition engine
└── references/
    └── etf_index_constituents.json        # Index constituents, weights, sector mappings
```
