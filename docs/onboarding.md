# Onboarding — Connecting Clients to This Workspace

## Google Antigravity (IDE / CLI)

1. Copy or symlink the skill into your Antigravity config:
   ```bash
   ln -s ~/MyDevArea/ai-workspace/plugins/kite-agent/latest/skills/kite-portfolio-lookthrough/latest \
     ~/.gemini/config/skills/kite-portfolio-lookthrough
   ```
2. Merge `configs/antigravity/mcp_config.json` into `~/.gemini/config/mcp_config.json`.

---

## Claude Desktop

1. Open `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Merge the contents of `configs/claude/claude_desktop_config.json`
3. Restart Claude Desktop
4. In your project's `CLAUDE.md`, add:
   ```markdown
   When asked to analyze Zerodha portfolio or ETF look-through exposure,
   follow the instructions in `plugins/kite-agent/latest/skills/kite-portfolio-lookthrough/latest/SKILL.md`.
   ```

---

## GitHub Copilot (VS Code)

1. Ensure the VS Code MCP extension is installed.
2. Merge `configs/copilot/mcp.json` into your VS Code MCP config.
3. In `.github/copilot-instructions.md` add:
   ```markdown
   When analyzing Kite portfolios, follow:
   `plugins/kite-agent/latest/skills/kite-portfolio-lookthrough/latest/SKILL.md`
   ```

---

## Any MCP-Compatible Client

Use `configs/generic/mcp_config.json` as a baseline and adapt to your client's config schema.

---

## Running a Local MCP Server

```bash
cd mcp-servers/<server-name>/latest
uv sync
uv run serve
```
