# MCP Resource Server with OAuth2 Protection
# This server provides protected tools/resources and validates tokens with the OAuth provider

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
import httpx
import asyncio
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth Provider configuration
OAUTH_PROVIDER_URL = "http://localhost:9000"
INTROSPECTION_ENDPOINT = f"{OAUTH_PROVIDER_URL}/introspect"

# Initialize MCP server
mcp = FastMCP("Protected Resource Server")

# Token cache to reduce introspection calls
token_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate an access token with the OAuth provider
    
    Returns token info if valid, raises exception if invalid
    """
    # Check cache first
    if token in token_cache:
        cached = token_cache[token]
        if cached.get("expires_at", 0) > asyncio.get_event_loop().time():
            logger.info(f"Token validated from cache for user: {cached.get('username')}")
            return cached
    
    # Introspect token with OAuth provider
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                INTROSPECTION_ENDPOINT,
                data={"token": token}
            )
            
            if response.status_code != 200:
                raise ValueError("Failed to introspect token")
            
            token_info = response.json()
            
            if not token_info.get("active"):
                raise ValueError("Token is not active")
            
            # Cache the token info
            token_info["expires_at"] = asyncio.get_event_loop().time() + CACHE_TTL
            token_cache[token] = token_info
            
            logger.info(f"Token validated for user: {token_info.get('username')}")
            return token_info
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise ValueError(f"Invalid token: {str(e)}")

def require_scope(required_scope: str):
    """Decorator to require a specific scope for a tool"""
    def decorator(func):
        @wraps(func)
        async def wrapper(token: str, *args, **kwargs):
            # Validate token and check scope
            token_info = await validate_token(token)
            scopes = token_info.get("scope", "").split()
            
            if required_scope not in scopes:
                raise PermissionError(f"This operation requires '{required_scope}' scope")
            
            # Add user context to kwargs with non-underscore names
            kwargs["user_context"] = token_info.get("username")
            kwargs["user_scopes"] = scopes
            
            # Pass token and all other args to the actual function
            return await func(token, *args, **kwargs)
        return wrapper
    return decorator

# Protected Tools/Resources

@mcp.tool()
async def get_user_profile(token: str) -> Dict[str, Any]:
    """
    Get the current user's profile (requires valid token)
    
    Args:
        token: OAuth2 access token
    """
    token_info = await validate_token(token)
    
    return {
        "username": token_info.get("username"),
        "client_id": token_info.get("client_id"),
        "scopes": token_info.get("scope", "").split(),
        "token_type": token_info.get("token_type"),
        "expires_at": token_info.get("exp")
    }

@mcp.tool()
@require_scope("read")
async def read_data(token: str, resource_id: str, user_context: str = None, user_scopes: list = None) -> Dict[str, Any]:
    """
    Read protected data (requires 'read' scope)
    
    Args:
        token: OAuth2 access token
        resource_id: ID of the resource to read
    """
    # Simulate reading data from a database
    data = {
        "doc1": {"title": "Document 1", "content": "This is a sample document", "owner": "alice"},
        "doc2": {"title": "Document 2", "content": "Another sample document", "owner": "bob"},
        "doc3": {"title": "Document 3", "content": "Admin only document", "owner": "admin"}
    }
    
    resource = data.get(resource_id)
    if not resource:
        return {"error": "Resource not found"}
    
    # Check if user can access this resource
    if resource["owner"] != user_context and "admin" not in user_scopes:
        return {"error": "Access denied - you don't own this resource"}
    
    return {
        "resource_id": resource_id,
        "data": resource,
        "accessed_by": user_context,
        "access_time": asyncio.get_event_loop().time()
    }

@mcp.tool()
@require_scope("write")
async def write_data(token: str, resource_id: str, content: str, user_context: str = None, user_scopes: list = None) -> Dict[str, str]:
    """
    Write protected data (requires 'write' scope)
    
    Args:
        token: OAuth2 access token
        resource_id: ID of the resource to write
        content: Content to write
    """
    # Simulate writing data
    return {
        "status": "success",
        "message": f"Data written to {resource_id}",
        "author": user_context,
        "content_preview": content[:100] if len(content) > 100 else content
    }

@mcp.tool()
@require_scope("admin")
async def admin_operation(token: str, operation: str, user_context: str = None, user_scopes: list = None) -> Dict[str, Any]:
    """
    Perform administrative operations (requires 'admin' scope)
    
    Args:
        token: OAuth2 access token
        operation: The admin operation to perform
    """
    operations = {
        "list_users": {
            "users": ["alice", "bob", "admin"],
            "total": 3
        },
        "system_status": {
            "status": "healthy",
            "uptime": "24 hours",
            "active_tokens": len(token_cache)
        },
        "clear_cache": {
            "cleared": len(token_cache),
            "status": "cache cleared"
        }
    }
    
    if operation == "clear_cache":
        token_cache.clear()
    
    result = operations.get(operation, {"error": "Unknown operation"})
    result["performed_by"] = user_context
    
    return result

@mcp.tool()
async def list_available_resources(token: str) -> Dict[str, Any]:
    """
    List resources available to the current user based on their scopes
    
    Args:
        token: OAuth2 access token
    """
    token_info = await validate_token(token)
    scopes = token_info.get("scope", "").split()
    username = token_info.get("username")
    
    available = {
        "resources": [],
        "operations": []
    }
    
    # Always available
    available["operations"].append("get_user_profile")
    available["operations"].append("list_available_resources")
    
    if "read" in scopes:
        available["operations"].append("read_data")
        available["resources"].extend(["doc1", "doc2"])
        if username == "admin" or "admin" in scopes:
            available["resources"].append("doc3")
    
    if "write" in scopes:
        available["operations"].append("write_data")
    
    if "admin" in scopes:
        available["operations"].append("admin_operation")
        available["resources"].append("all_resources")
    
    return {
        "user": username,
        "scopes": scopes,
        "available": available
    }

@mcp.tool()
async def public_info() -> Dict[str, Any]:
    """
    Get public information (no authentication required)
    """
    return {
        "server": "MCP Protected Resource Server",
        "version": "1.0.0",
        "oauth_provider": OAUTH_PROVIDER_URL,
        "authentication": "Required for most operations",
        "public_endpoints": ["public_info"],
        "protected_endpoints": [
            "get_user_profile",
            "read_data (requires 'read' scope)",
            "write_data (requires 'write' scope)",
            "admin_operation (requires 'admin' scope)",
            "list_available_resources"
        ]
    }

# Error handler for authentication errors
@mcp.tool()
async def handle_auth_error(error_type: str, error_description: str) -> Dict[str, str]:
    """
    Handle authentication/authorization errors
    
    Args:
        error_type: Type of error (invalid_token, insufficient_scope, etc.)
        error_description: Detailed error description
    """
    error_responses = {
        "invalid_token": {
            "error": "invalid_token",
            "error_description": error_description,
            "resolution": "Please obtain a new token from the OAuth provider"
        },
        "insufficient_scope": {
            "error": "insufficient_scope",
            "error_description": error_description,
            "resolution": "Request additional scopes when obtaining token"
        },
        "token_expired": {
            "error": "token_expired",
            "error_description": error_description,
            "resolution": "Use refresh token to obtain new access token"
        }
    }
    
    return error_responses.get(error_type, {
        "error": error_type,
        "error_description": error_description
    })

if __name__ == "__main__":
    import sys
    # Determine transport mode from command line argument
    # Valid options: stdio, sse, streamable-http
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    print("MCP Protected Resource Server")
    print("=" * 50)
    print(f"OAuth Provider: {OAUTH_PROVIDER_URL}")
    print("\nThis server validates tokens with the OAuth provider")
    print("All protected operations require a valid access token")
    print("\nProtected endpoints require these scopes:")
    print("  - read_data: 'read' scope")
    print("  - write_data: 'write' scope")
    print("  - admin_operation: 'admin' scope")
    print("\nStarting MCP server...")

    mcp.run(transport=transport)