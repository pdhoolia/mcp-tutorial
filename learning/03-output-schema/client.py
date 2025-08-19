import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_weather_service():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "learning/03-output-schema/server.py", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get weather for a single city
            result = await session.call_tool("get_weather", {"city": "London"})
            print("Weather in London:")
            print(json.dumps(result.structuredContent, indent=2))
            
            # Compare multiple cities
            result = await session.call_tool(
                "compare_weather", 
                {"cities": ["London", "Paris", "Tokyo"]}
            )
            print("\nWeather comparison:")
            print(json.dumps(result.structuredContent, indent=2))

if __name__ == "__main__":
    asyncio.run(test_weather_service())