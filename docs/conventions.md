# Workspace Conventions

## Versioning Policy

All skills, prompts, agents, MCP servers, and plugins are versioned using explicit directories.

### Version bump rules

| Change type | Action |
|-------------|--------|
| Bug fix, wording update, non-breaking improvement | Edit in-place within the current `vN/` directory |
| New optional field, additive change | Edit in-place, bump patch in frontmatter only |
| Breaking change (tool renamed, arg removed, workflow restructured) | Create a new `vN+1/` directory; update the `latest` symlink |

### `latest` symlink

Every versioned directory has a `latest` symlink pointing to the current stable version:
```bash
ln -s v1 latest      # first release
ln -sfn v2 latest    # promote v2 to latest
```

Clients should reference `latest` unless they need to pin to a specific version.

---

## Naming Conventions

| Item | Format | Example |
|------|--------|---------|
| Skill directory | `kebab-case` | `kite-portfolio-lookthrough` |
| Prompt directory | `kebab-case` | `financial-analysis-system` |
| Agent directory | `kebab-case` | `kite-agent` |
| MCP server directory | `kebab-case` | `market-data-server` |
| Plugin directory | `kebab-case` | `kite-agent` |
| Python package | `snake_case` | `market_data_server` |

---

## File Naming

| File | Required in |
|------|------------|
| `SKILL.md` | Every skill version |
| `AGENT.md` | Every agent and plugin version |
| `plugin.json` | Every plugin version |
| `mcp_config.json` | Every plugin version |
| `system_prompt.md` | Every agent and plugin version |
| `pyproject.toml` | Every MCP server version |
| `.env.example` | Every MCP server version |

---

## What to commit vs. ignore

| File | Committed |
|------|-----------|
| `SKILL.md`, `AGENT.md`, `plugin.json` | ✅ |
| `.env.example` | ✅ |
| `uv.lock` | ✅ |
| `pyproject.toml` | ✅ |
| `.env` | ❌ (gitignored) |
| `.venv/` | ❌ (gitignored) |
| `__pycache__/` | ❌ (gitignored) |
| `latest` symlinks | ✅ (tracked via `.gitattributes`) |
