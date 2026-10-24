# MCP Server Template

> **Stack:** Python · FastMCP · uv

A template for building MCP servers in Python. Each server is an isolated Python project.

## Tools Exposed

| Tool | Description | Parameters |
|------|-------------|------------|
| `example_tool` | Example placeholder tool | `query: str` |

## Environment Variables

See `.env.example` for all required variables.

## Running Locally

```bash
uv sync
uv run serve
```

## Running in Claude Desktop / Copilot

Add to your client's MCP config:
```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "uv",
      "args": ["--directory", "/path/to/this/server", "run", "serve"]
    }
  }
}
```
