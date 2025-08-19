# Based on examples/snippets/clients/stdio_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_calculator_client():
    # Connect to our calculator server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "learning/01-hello-world/server.py", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            
            # Call the add tool
            result = await session.call_tool("add", {"a": 5, "b": 3})
            print(f"5 + 3 = {result.content[0].text}")
            
            # Call the multiply tool
            result = await session.call_tool("multiply", {"a": 4, "b": 7})
            print(f"4 * 7 = {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(run_calculator_client())