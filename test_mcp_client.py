
import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main():
    server_file = Path(__file__).with_name("mcp_server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    async with Client(server_params) as client:
        response = await client.list_tools()

        print("\nMCP connection successful!")
        print("\nAvailable GraphSleuth tools:")

        for tool in response.tools:
            print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
