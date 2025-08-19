# Simplified auth example based on examples/servers/simple-auth
from mcp.server.fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("Secure Service")

# Simple token storage (in production, use proper storage)
valid_tokens = {
    "demo-token-123": {"user": "alice", "permissions": ["read", "write"]},
    "demo-token-456": {"user": "bob", "permissions": ["read"]}
}

def verify_token(token: str) -> Optional[dict]:
    """Verify a token and return user info"""
    return valid_tokens.get(token)

@mcp.tool()
def secure_operation(token: str, operation: str, data: str) -> str:
    """Perform a secure operation with token validation"""
    user_info = verify_token(token)
    
    if not user_info:
        raise ValueError("Invalid token")
    
    if operation == "write" and "write" not in user_info["permissions"]:
        raise ValueError(f"User {user_info['user']} lacks write permission")
    
    # Perform the operation
    if operation == "read":
        return f"User {user_info['user']} read data: {data}"
    elif operation == "write":
        return f"User {user_info['user']} wrote data: {data}"
    else:
        raise ValueError(f"Unknown operation: {operation}")

@mcp.tool()
def generate_token(username: str, password: str) -> str:
    """Generate a token (demo only - not secure!)"""
    # In production, properly validate credentials
    if username == "alice" and password == "secret123":
        return "demo-token-123"
    elif username == "bob" and password == "secret456":
        return "demo-token-456"
    else:
        raise ValueError("Invalid credentials")

if __name__ == "__main__":
    mcp.run()