# Kite Portfolio Look-Through Plugin

A universal, agent-agnostic plugin for analyzing Zerodha Kite portfolios. It connects to the user's account via the standard Model Context Protocol (MCP), extracts holdings, and decomposes equity index ETFs (e.g. `NV20`, `NIFTYIETF`, `BANKBEES`, `ITBEES`) into their underlying constituent stocks to reveal true look-through equity exposure and sector allocation.

---

## Agent Compatibility & Quick-Start

### 1. Anthropic Claude (Claude Desktop / Project)
- **MCP Config**: Add the `kite` entry from `mcp_config.json` to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`).
- **Prompt / Rules**: Reference this skill in your project's `CLAUDE.md`:
  ```markdown
  When asked to analyze Kite portfolios or ETF look-through exposure,
  follow `plugins/kite-portfolio-lookthrough/latest/skills/kite-portfolio-lookthrough/latest/SKILL.md`.
  ```

### 2. GitHub Copilot (VS Code / CLI)
- **MCP Config**: Add the `kite` server configuration to your VS Code MCP settings (`.vscode/mcp.json`).
- **Instructions**: Reference this skill in `.github/copilot-instructions.md`:
  ```markdown
  When analyzing Zerodha Kite portfolios, follow:
  `plugins/kite-portfolio-lookthrough/latest/skills/kite-portfolio-lookthrough/latest/SKILL.md`
  ```

### 3. Google Antigravity (IDE / CLI)
- Symlink the skill or plugin into your Antigravity config:
  ```bash
  ln -s ~/MyDevArea/ai-workspace/plugins/kite-portfolio-lookthrough/latest/skills/kite-portfolio-lookthrough/latest \
    ~/.gemini/config/skills/kite-portfolio-lookthrough
  ```
- Or run with slash command `/kite-portfolio-lookthrough` or `agy -i "/kite-portfolio-lookthrough"`.

---

## Structure

```
kite-portfolio-lookthrough/v1/
├── plugin.json
├── AGENT.md
├── system_prompt.md
├── mcp_config.json
├── README.md
└── skills/kite-portfolio-lookthrough/
    ├── latest -> v1/
    └── v1/
        ├── SKILL.md
        ├── README.md
        ├── references/etf_index_constituents.json
        └── scripts/
            ├── decompose_portfolio.py
            └── update_constituents.py
```
