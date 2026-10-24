"""MCP Server Template — FastMCP entrypoint."""

from dotenv import load_dotenv
from fastmcp import FastMCP

from tools.example import register_tools

load_dotenv()

mcp = FastMCP(
    name="mcp-server-template",
    description="Template MCP server. Replace with your server's description.",
)

register_tools(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
