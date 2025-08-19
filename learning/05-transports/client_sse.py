#!/usr/bin/env python
"""
Simple SSE client to test the weather server in SSE mode.
Run the server first: uv run python learning/05-transports/server.py sse
Then run this client: uv run python learning/05-transports/client_sse.py
"""

import asyncio
import json
import httpx

async def test_sse_server():
    """Test the SSE server."""
    base_url = "http://localhost:8000"
    
    print("Connecting to SSE endpoint...")
    
    # Use a single client for the entire session
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Connect to SSE endpoint and keep it open
        async with client.stream("GET", f"{base_url}/sse") as sse_response:
            session_id = None
            message_url = None
            
            # Create an async queue for communication between reader and sender
            response_queue = asyncio.Queue()
            
            # Create a task to read SSE events
            async def read_sse_events():
                """Read events from the SSE stream."""
                try:
                    async for line in sse_response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data:
                                # First message should be the endpoint URL
                                if not session_id and "session_id=" in data:
                                    await response_queue.put(("endpoint", data))
                                else:
                                    # Try to parse as JSON
                                    try:
                                        event = json.loads(data)
                                        print(f"\nSSE Response: {json.dumps(event, indent=2)}")
                                        await response_queue.put(("json", event))
                                    except json.JSONDecodeError:
                                        print(f"\nSSE Data: {data}")
                                        await response_queue.put(("text", data))
                except Exception as e:
                    print(f"SSE reader error: {e}")
                    await response_queue.put(("error", str(e)))
            
            # Start the SSE reader task
            sse_task = asyncio.create_task(read_sse_events())
            
            try:
                # Wait for the endpoint message
                print("Waiting for endpoint...")
                msg_type, data = await asyncio.wait_for(response_queue.get(), timeout=5.0)
                if msg_type == "endpoint" and "session_id=" in data:
                    message_url = data
                    session_id = data.split("session_id=")[1]
                    print(f"Got session_id: {session_id}")
                    print(f"Message endpoint: {message_url}")
                else:
                    print(f"Unexpected first message: {msg_type} - {data}")
                    return
                
                # Now send messages while keeping SSE connection alive
                
                # Initialize the connection
                print("\n--- Sending initialize ---")
                response = await client.post(
                    f"{base_url}/messages?session_id={session_id}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "0.1.0",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "test-client",
                                "version": "1.0.0"
                            }
                        },
                        "id": 1
                    }
                )
                print(f"POST Response: {response.status_code} {response.text}")
                
                # Wait for the initialization response - THIS IS CRITICAL
                try:
                    msg_type, data = await asyncio.wait_for(response_queue.get(), timeout=5.0)
                    if msg_type == "json" and "result" in data:
                        print("Initialization successful!")
                    else:
                        print(f"Initialization failed: {data}")
                        return
                except asyncio.TimeoutError:
                    print("No response received for initialize - cannot continue")
                    return
                
                # Send initialized notification to complete the handshake
                print("\n--- Sending initialized notification ---")
                response = await client.post(
                    f"{base_url}/messages?session_id={session_id}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                        # No id for notifications
                    }
                )
                print(f"POST Response: {response.status_code} {response.text}")
                
                # Small delay to ensure the server processes the notification
                await asyncio.sleep(0.5)
                
                # List tools
                print("\n--- Sending tools/list ---")
                response = await client.post(
                    f"{base_url}/messages?session_id={session_id}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "id": 2
                    }
                )
                print(f"POST Response: {response.status_code} {response.text}")
                
                # Wait for and display the response
                try:
                    msg_type, data = await asyncio.wait_for(response_queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    print("No response received for tools/list")
                
                # Test a tool call
                print("\n--- Calling get_weather tool ---")
                response = await client.post(
                    f"{base_url}/messages?session_id={session_id}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "get_weather",
                            "arguments": {
                                "city": "London"
                            }
                        },
                        "id": 3
                    }
                )
                print(f"POST Response: {response.status_code} {response.text}")
                
                # Wait for and display the response
                try:
                    msg_type, data = await asyncio.wait_for(response_queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    print("No response received for get_weather")
                
                # List resources
                print("\n--- Listing resources ---")
                response = await client.post(
                    f"{base_url}/messages?session_id={session_id}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "resources/list",
                        "id": 4
                    }
                )
                print(f"POST Response: {response.status_code} {response.text}")
                
                # Wait for and display the response
                try:
                    msg_type, data = await asyncio.wait_for(response_queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    print("No response received for resources/list")
                
                print("\n--- Test completed ---")
                
            finally:
                # Cancel the SSE reader task
                sse_task.cancel()
                try:
                    await sse_task
                except asyncio.CancelledError:
                    pass

if __name__ == "__main__":
    print("SSE Test Client")
    print("=" * 50)
    print("Make sure the server is running with:")
    print("  uv run python learning/05-transports/server.py sse")
    print("=" * 50)
    
    try:
        asyncio.run(test_sse_server())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()