# Test file for the calculator server from learning/01-hello-world
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

# Import the server module
import sys
sys.path.append('learning/01-hello-world')

from server import mcp  # Assuming we saved Module 1's server

@pytest.mark.anyio
async def test_add_tool():
    """Test the add tool"""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        assert "8" in result.content[0].text

@pytest.mark.anyio
async def test_multiply_tool():
    """Test the multiply tool"""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("multiply", {"a": 4, "b": 7})
        assert "28" in result.content[0].text

@pytest.mark.anyio
async def test_divide_by_zero():
    """Test divide by zero error handling"""
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        result = await client.call_tool("divide", {"a": 10, "b": 0})
        assert result.isError is True
        assert "Cannot divide by zero" in str(result.content[0].text)
