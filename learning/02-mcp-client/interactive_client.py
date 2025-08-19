# Interactive calculator client
import asyncio

from pydantic import AnyUrl
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def interactive_calculator():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "learning/01-hello-world/server_with_resources.py", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Calculator Ready! Commands: add, multiply, divide, history, quit")
            
            while True:
                command = input("\n> ").strip().lower()
                
                if command == "quit":
                    break
                elif command == "history":
                    # Read the history resource
                    result = await session.read_resource(AnyUrl("history://recent"))
                    print(result.contents[0].text)
                elif command in ["add", "multiply", "divide"]:
                    try:
                        a = float(input("First number: "))
                        b = float(input("Second number: "))
                        result = await session.call_tool(command, {"a": a, "b": b})
                        print(f"Result: {result.content[0].text}")
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    print("Unknown command")

if __name__ == "__main__":
    asyncio.run(interactive_calculator())