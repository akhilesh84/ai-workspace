"""Example tool — replace or delete this file."""

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def example_tool(query: str) -> str:
        """An example tool. Replace with your actual tool logic.

        Args:
            query: The input query string.

        Returns:
            A response string.
        """
        return f"You queried: {query}"
