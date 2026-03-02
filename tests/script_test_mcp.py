"""Manual test client for the aurumaide MCP server.

Run via: python -m tests.script_test_mcp
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aurumaide.google.mcp"],
    )

    async with (
        stdio_client(server_params) as (read, write),
        ClientSession(read, write) as session,
    ):
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Call google_ai
            query = " ".join(sys.argv[1:]) or "What is the capital of France?"
            print(f"\nCalling google_ai({query!r})...")
            result = await session.call_tool("google_ai", {"query": query})
            print(f"\nResult:\n{result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
