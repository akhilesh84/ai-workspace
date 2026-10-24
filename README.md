# ai-workspace

A universal, agent-agnostic workspace for building and sharing **skills**, **prompts**, **agents**, and **MCP servers** that work across any AI agent platform — Claude, GitHub Copilot, Google Antigravity, or any MCP-compatible client.

---

## Structure

```
ai-workspace/
├── skills/          # Shared, reusable skill definitions (versioned)
├── prompts/         # Shared prompt library (versioned)
├── agents/          # Standalone agent definitions (versioned)
├── mcp-servers/     # Shared MCP server implementations in Python (versioned)
├── plugins/         # Self-contained agent bundles (agent + skills + MCP + prompts)
├── configs/         # Client-specific MCP wiring configs
└── docs/            # Conventions, onboarding, authoring guides
```

## Quick Start

1. **Clone this repo**
   ```bash
   git clone <repo-url> ai-workspace
   cd ai-workspace
   ```

2. **Wire up your AI client** — see [`docs/onboarding.md`](docs/onboarding.md)

3. **Use a plugin** — copy the relevant `mcp_config.json` from a plugin to your client config

4. **Run an MCP server locally**
   ```bash
   cd mcp-servers/<server-name>/latest
   uv sync
   uv run serve
   ```

## Versioning

Every skill, prompt, agent, MCP server, and plugin is versioned with `v1/`, `v2/` directories. A `latest` symlink always points to the current stable version. See [`docs/conventions.md`](docs/conventions.md).

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, production-ready |
| `dev`  | Active development |
| `feat/<name>` | Feature branches |

---

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [`kite-agent`](plugins/kite-agent/latest/) | Zerodha Kite portfolio look-through analysis |
