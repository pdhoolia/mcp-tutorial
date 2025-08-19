from dotenv import load_dotenv
load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


async def main():
    client = MultiServerMCPClient(
        {
            "weather": {
                "command": "uv",
                "args": ["run", "python", "learning/05-transports/server.py"],
                "transport": "stdio",
            },
            "math": {
                "command": "uv",
                "args": ["run", "python", "learning/01-hello-world/server_with_resources.py"],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    agent = create_react_agent(
        "openai:gpt-4o-mini",
        tools
    )
    question = "what's (3 + 5) x 12?"
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    print(f"You asked: {question}")
    print(math_response.get("messages")[-1].content)

    question = "what is the current weather in nyc?"
    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    print(f"You asked: {question}")
    print(weather_response.get("messages")[-1].content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())