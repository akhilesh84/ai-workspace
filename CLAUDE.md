# Instructions for Claude

## Available Skills & Plugins

### Kite Portfolio Look-Through Analysis
When the user asks to analyze their Zerodha Kite portfolio, view equity look-through exposure, or decompose ETFs into underlying constituent stocks, follow the workflow defined in:
[`skills/kite-portfolio-lookthrough/latest/SKILL.md`](skills/kite-portfolio-lookthrough/latest/SKILL.md)

### MCP Configuration
- **Kite MCP Server**: `npx mcp-remote https://mcp.kite.trade/mcp` (provides `get_profile`, `login`, `get_holdings`).
- Merge `configs/claude/claude_desktop_config.json` into your Claude Desktop configuration if using the desktop client.
