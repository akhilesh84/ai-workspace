"""Nifty Energy Quality Basket MCP Server — FastMCP entrypoint."""

import sys
from pathlib import Path

# Ensure src/server directory is available on sys.path for direct module runs
server_dir = Path(__file__).resolve().parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

from dotenv import load_dotenv

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

try:
    from tools.energy_basket import register_tools
except ImportError:
    from server.tools.energy_basket import register_tools

load_dotenv()

mcp = FastMCP(
    name="Nifty Energy Quality Basket Server",
)


register_tools(mcp)


def main() -> None:
    """Run the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
