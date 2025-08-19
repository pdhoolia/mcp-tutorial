#!/usr/bin/env python
"""
Streamable HTTP client for Task Manager MCP Server
This client populates tasks for MCP learning modules
"""

import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Task definitions for MCP learning modules
MCP_LEARNING_TASKS = [
    # Module 1 - Hello World (completed)
    {
        "title": "Module 1: Hello World",
        "description": "Understand MCP client-server architecture, build and run first MCP server, test servers using MCP Inspector",
        "priority": 5,
        "tags": ["learning", "basics", "module-1"],
        "status": "completed"
    },
    {
        "title": "Exercise 1.1: Your First MCP Server",
        "description": "Build hello-world/server.py and test with MCP Inspector",
        "priority": 4,
        "tags": ["exercise", "module-1"],
        "status": "completed"
    },
    {
        "title": "Exercise 1.2: Adding Resources",
        "description": "Extend server with resources in server_with_resources.py",
        "priority": 4,
        "tags": ["exercise", "module-1"],
        "status": "completed"
    },
    
    # Module 2 - Client-Server Communication (completed)
    {
        "title": "Module 2: Client-Server Communication",
        "description": "Build MCP clients, understand request-response patterns, handle tool calls programmatically",
        "priority": 5,
        "tags": ["learning", "client", "module-2"],
        "status": "completed"
    },
    {
        "title": "Exercise 2.1: Building a Simple Client",
        "description": "Create and run mcp-client/client.py",
        "priority": 4,
        "tags": ["exercise", "module-2"],
        "status": "completed"
    },
    {
        "title": "Exercise 2.2: Interactive Client",
        "description": "Build interactive_client.py with user input handling",
        "priority": 4,
        "tags": ["exercise", "module-2"],
        "status": "completed"
    },
    
    # Module 3 - Output Schema (completed)
    {
        "title": "Module 3: Output Schema",
        "description": "Use Pydantic models for structured data, implement type validation, return complex data structures",
        "priority": 5,
        "tags": ["learning", "schema", "module-3"],
        "status": "completed"
    },
    {
        "title": "Exercise 3: Weather Service with Structured Output",
        "description": "Build weather service with Pydantic models in output-schema/server.py",
        "priority": 4,
        "tags": ["exercise", "module-3"],
        "status": "completed"
    },
    
    # Module 4 - Prompts & Templates (completed)
    {
        "title": "Module 4: Prompts & Templates",
        "description": "Create reusable prompt templates, build context-aware prompts, implement prompt parameters",
        "priority": 5,
        "tags": ["learning", "prompts", "module-4"],
        "status": "completed"
    },
    {
        "title": "Exercise 4.1: Code Review Assistant",
        "description": "Create code review prompt templates in prompts/server.py",
        "priority": 4,
        "tags": ["exercise", "module-4"],
        "status": "completed"
    },
    {
        "title": "Exercise 4.2: Prompts Client",
        "description": "Build client to use prompt templates with LLMs",
        "priority": 4,
        "tags": ["exercise", "module-4"],
        "status": "completed"
    },
    
    # Module 5 - Transport Protocols (in-progress)
    {
        "title": "Module 5: Transport Protocols",
        "description": "Understand stdio vs HTTP transports, implement HTTP-based MCP servers, handle multiple transport types",
        "priority": 5,
        "tags": ["learning", "transport", "module-5"],
        "status": "in_progress"
    },
    {
        "title": "Exercise 5.1: Server with SSE transport",
        "description": "Implement SSE transport in transports/server.py",
        "priority": 4,
        "tags": ["exercise", "module-5"],
        "status": "in_progress"
    },
    {
        "title": "Exercise 5.2: Server with Streamable-http transport",
        "description": "Add streamable-http transport support",
        "priority": 4,
        "tags": ["exercise", "module-5"],
        "status": "pending"
    },
    
    # Module 6 - Authentication & Security (pending)
    {
        "title": "Module 6: Authentication & Security",
        "description": "Basics of authorization, OAuth implementation, securing MCP resources",
        "priority": 5,
        "tags": ["learning", "security", "module-6"],
        "status": "pending"
    },
    {
        "title": "Exercise 6.1: Basic Authorization",
        "description": "Implement basic authorization in auth/basic-design/server.py",
        "priority": 4,
        "tags": ["exercise", "module-6"],
        "status": "pending"
    },
    {
        "title": "Exercise 6.2: OAuth Implementation",
        "description": "Build OAuth provider and resource server",
        "priority": 4,
        "tags": ["exercise", "module-6"],
        "status": "pending"
    },
    {
        "title": "Exercise 6.3: Full OAuth Design",
        "description": "Separate OAuth provider and MCP resource servers",
        "priority": 4,
        "tags": ["exercise", "module-6"],
        "status": "pending"
    },
    
    # Module 7 - Pytest (pending)
    {
        "title": "Module 7: Pytest",
        "description": "Learn how to write pytests for MCP servers",
        "priority": 4,
        "tags": ["learning", "testing", "module-7"],
        "status": "pending"
    },
    {
        "title": "Exercise 7: Testing MCP Tools",
        "description": "Write tests using create_connected_server_and_client_session",
        "priority": 3,
        "tags": ["exercise", "module-7"],
        "status": "pending"
    },
    
    # Module 8 - Capstone (pending)
    {
        "title": "Module 8: Capstone Project",
        "description": "Complete task management MCP server demonstrating all learned concepts",
        "priority": 5,
        "tags": ["learning", "capstone", "module-8"],
        "status": "pending"
    },
    {
        "title": "Exercise 8: Build Complete Task Manager",
        "description": "Integrate all MCP concepts in a task management server",
        "priority": 5,
        "tags": ["exercise", "module-8"],
        "status": "pending"
    }
]

async def populate_learning_tasks():
    """Connect to Task Manager server and populate learning module tasks"""
    
    # Server URL for streamable HTTP transport
    server_url = "http://localhost:8000/mcp"
    
    print("Connecting to Task Manager MCP Server...")
    
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            print("✓ Connected to server")
            
            # List available tools
            tools = await session.list_tools()
            print(f"✓ Found {len(tools.tools)} tools available")
            
            # Create tasks for each learning module
            print("\nCreating learning module tasks...")
            created_tasks = []
            
            for task_data in MCP_LEARNING_TASKS:
                # Create the task
                result = await session.call_tool(
                    "create_task",
                    arguments={
                        "title": task_data["title"],
                        "description": task_data["description"],
                        "priority": task_data["priority"],
                        "tags": task_data["tags"]
                    }
                )
                
                if result.content and len(result.content) > 0:
                    task = json.loads(result.content[0].text)
                    created_tasks.append(task)
                    
                    # Update status if not pending
                    if task_data["status"] != "pending":
                        status_result = await session.call_tool(
                            "update_task_status",
                            arguments={
                                "task_id": task["id"],
                                "status": task_data["status"]
                            }
                        )
                        
                    print(f"  ✓ Created: {task_data['title']} [{task_data['status']}]")
            
            print(f"\n✓ Successfully created {len(created_tasks)} tasks")
            
            # Get task statistics
            print("\nFetching task statistics...")
            stats_result = await session.call_tool("get_task_stats", arguments={})
            
            if stats_result.content and len(stats_result.content) > 0:
                stats = json.loads(stats_result.content[0].text)
                print("\nTask Statistics:")
                print(f"  Total Tasks: {stats['total_tasks']}")
                print(f"  Completed: {stats['by_status']['completed']}")
                print(f"  In Progress: {stats['by_status']['in_progress']}")
                print(f"  Pending: {stats['by_status']['pending']}")
                print(f"  Completion Rate: {stats['completion_rate']}%")
                print(f"  Average Priority: {stats['average_priority']}/5")
            
            # Get task summary resource
            print("\nFetching task summary resource...")
            resources = await session.list_resources()
            
            for resource in resources.resources:
                if resource.uri == "tasks://summary":
                    summary_result = await session.read_resource(resource.uri)
                    if summary_result.contents and len(summary_result.contents) > 0:
                        print("\n" + summary_result.contents[0].text)
                    break
            
            print("\n✓ Task population complete!")

async def main():
    """Main entry point"""
    print("MCP Learning Tasks Populator")
    print("============================")
    print("\nThis client will populate the Task Manager with MCP learning module tasks.")
    print("\nMake sure the server is running with streamable-http transport:")
    print("  uv run python learning/08-capstone/server.py streamable-http")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
        await populate_learning_tasks()
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the server is running on http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(main())