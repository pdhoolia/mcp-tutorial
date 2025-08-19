# Full OAuth2 server implementation with MCP
# Demonstrates authorization code flow, token management, and scope validation
from mcp.server.fastmcp import FastMCP
from typing import Optional, Dict, Any
import secrets
import time
import hashlib
from datetime import datetime

mcp = FastMCP("OAuth2 Server")

# In-memory storage (use database in production)
class OAuth2Storage:
    def __init__(self):
        # Registered OAuth clients
        self.clients = {
            "demo-client-id": {
                "client_secret": "demo-client-secret",
                "redirect_uris": ["http://localhost:8080/callback"],
                "allowed_scopes": ["read", "write", "profile", "admin"],
                "name": "Demo Application"
            }
        }
        
        # User accounts
        self.users = {
            "alice": {
                "password_hash": self._hash_password("password123"),
                "email": "alice@example.com",
                "scopes": ["read", "write", "profile"]
            },
            "admin": {
                "password_hash": self._hash_password("admin123"),
                "email": "admin@example.com", 
                "scopes": ["read", "write", "profile", "admin"]
            }
        }
        
        # Active authorization codes (temporary)
        self.auth_codes = {}  # code -> {client_id, user, scopes, expires_at, redirect_uri}
        
        # Active access tokens
        self.access_tokens = {}  # token -> {client_id, user, scopes, expires_at}
        
        # Refresh tokens
        self.refresh_tokens = {}  # token -> {client_id, user, scopes}
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        if not user:
            return False
        return user["password_hash"] == self._hash_password(password)

storage = OAuth2Storage()

@mcp.tool()
def oauth_authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: str,
    state: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """
    OAuth2 authorization endpoint - initiates authorization code flow
    
    Args:
        client_id: OAuth client identifier
        redirect_uri: Where to redirect after authorization
        response_type: Must be 'code' for authorization code flow
        scope: Space-separated list of requested scopes
        state: Optional state parameter for CSRF protection
        username: User's username (for demo - normally done via web UI)
        password: User's password (for demo - normally done via web UI)
    """
    # Validate client
    client = storage.clients.get(client_id)
    if not client:
        return {"error": "invalid_client", "error_description": "Unknown client"}
    
    # Validate redirect URI
    if redirect_uri not in client["redirect_uris"]:
        return {"error": "invalid_request", "error_description": "Invalid redirect URI"}
    
    # Validate response type
    if response_type != "code":
        return {"error": "unsupported_response_type", "error_description": "Only 'code' is supported"}
    
    # Parse requested scopes
    requested_scopes = scope.split()
    for s in requested_scopes:
        if s not in client["allowed_scopes"]:
            return {"error": "invalid_scope", "error_description": f"Scope '{s}' not allowed for client"}
    
    # Authenticate user (normally done via web UI)
    if not username or not password:
        return {
            "status": "authentication_required",
            "message": "User authentication required. Please provide username and password.",
            "client_name": client["name"],
            "requested_scopes": requested_scopes
        }
    
    if not storage.verify_password(username, password):
        return {"error": "access_denied", "error_description": "Invalid credentials"}
    
    user = storage.users[username]
    
    # Check if user has the requested scopes
    for s in requested_scopes:
        if s not in user["scopes"]:
            return {"error": "invalid_scope", "error_description": f"User lacks scope '{s}'"}
    
    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    storage.auth_codes[auth_code] = {
        "client_id": client_id,
        "user": username,
        "scopes": requested_scopes,
        "expires_at": time.time() + 600,  # 10 minutes
        "redirect_uri": redirect_uri
    }
    
    # Build redirect URL
    redirect_url = f"{redirect_uri}?code={auth_code}"
    if state:
        redirect_url += f"&state={state}"
    
    return {
        "status": "success",
        "redirect_to": redirect_url,
        "message": f"User {username} authorized. Redirecting with authorization code."
    }

@mcp.tool()
def oauth_token(
    grant_type: str,
    code: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
    scope: Optional[str] = None
) -> Dict[str, Any]:
    """
    OAuth2 token endpoint - exchanges authorization code or refresh token for access token
    
    Args:
        grant_type: 'authorization_code', 'refresh_token', or 'client_credentials'
        code: Authorization code (for authorization_code grant)
        redirect_uri: Must match the one used in authorize (for authorization_code grant)
        client_id: Client identifier
        client_secret: Client secret
        refresh_token: Refresh token (for refresh_token grant)
        scope: Optional scope restriction for refresh_token grant
    """
    # Validate client credentials
    if not client_id or not client_secret:
        return {"error": "invalid_client", "error_description": "Missing client credentials"}
    
    client = storage.clients.get(client_id)
    if not client or client["client_secret"] != client_secret:
        return {"error": "invalid_client", "error_description": "Invalid client credentials"}
    
    if grant_type == "authorization_code":
        # Exchange authorization code for tokens
        if not code:
            return {"error": "invalid_request", "error_description": "Missing authorization code"}
        
        auth_info = storage.auth_codes.get(code)
        if not auth_info:
            return {"error": "invalid_grant", "error_description": "Invalid authorization code"}
        
        # Validate code hasn't expired
        if time.time() > auth_info["expires_at"]:
            del storage.auth_codes[code]
            return {"error": "invalid_grant", "error_description": "Authorization code expired"}
        
        # Validate client matches
        if auth_info["client_id"] != client_id:
            return {"error": "invalid_grant", "error_description": "Code was issued to different client"}
        
        # Validate redirect URI matches
        if redirect_uri != auth_info["redirect_uri"]:
            return {"error": "invalid_grant", "error_description": "Redirect URI mismatch"}
        
        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token_value = secrets.token_urlsafe(32)
        
        # Store tokens
        storage.access_tokens[access_token] = {
            "client_id": client_id,
            "user": auth_info["user"],
            "scopes": auth_info["scopes"],
            "expires_at": time.time() + 3600  # 1 hour
        }
        
        storage.refresh_tokens[refresh_token_value] = {
            "client_id": client_id,
            "user": auth_info["user"],
            "scopes": auth_info["scopes"]
        }
        
        # Remove used authorization code
        del storage.auth_codes[code]
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token_value,
            "scope": " ".join(auth_info["scopes"])
        }
    
    elif grant_type == "refresh_token":
        # Exchange refresh token for new access token
        if not refresh_token:
            return {"error": "invalid_request", "error_description": "Missing refresh token"}
        
        refresh_info = storage.refresh_tokens.get(refresh_token)
        if not refresh_info:
            return {"error": "invalid_grant", "error_description": "Invalid refresh token"}
        
        # Validate client matches
        if refresh_info["client_id"] != client_id:
            return {"error": "invalid_grant", "error_description": "Token was issued to different client"}
        
        # Handle scope restriction
        if scope:
            requested_scopes = scope.split()
            for s in requested_scopes:
                if s not in refresh_info["scopes"]:
                    return {"error": "invalid_scope", "error_description": f"Scope '{s}' not in original grant"}
            scopes = requested_scopes
        else:
            scopes = refresh_info["scopes"]
        
        # Generate new access token
        access_token = secrets.token_urlsafe(32)
        storage.access_tokens[access_token] = {
            "client_id": client_id,
            "user": refresh_info["user"],
            "scopes": scopes,
            "expires_at": time.time() + 3600
        }
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(scopes)
        }
    
    elif grant_type == "client_credentials":
        # Client credentials flow (no user involved)
        # Generate access token for client itself
        access_token = secrets.token_urlsafe(32)
        
        # Use client's allowed scopes
        scopes = scope.split() if scope else client["allowed_scopes"]
        for s in scopes:
            if s not in client["allowed_scopes"]:
                return {"error": "invalid_scope", "error_description": f"Scope '{s}' not allowed"}
        
        storage.access_tokens[access_token] = {
            "client_id": client_id,
            "user": None,  # No user for client credentials
            "scopes": scopes,
            "expires_at": time.time() + 3600
        }
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(scopes)
        }
    
    else:
        return {"error": "unsupported_grant_type", "error_description": f"Grant type '{grant_type}' not supported"}

@mcp.tool()
def oauth_introspect(token: str, token_type_hint: Optional[str] = "access_token") -> Dict[str, Any]:
    """
    OAuth2 token introspection - validates and returns token information
    
    Args:
        token: The token to introspect
        token_type_hint: Hint about token type ('access_token' or 'refresh_token')
    """
    # Check access tokens first
    token_info = storage.access_tokens.get(token)
    if token_info:
        is_active = time.time() < token_info["expires_at"]
        return {
            "active": is_active,
            "scope": " ".join(token_info["scopes"]),
            "client_id": token_info["client_id"],
            "username": token_info["user"],
            "token_type": "Bearer",
            "exp": int(token_info["expires_at"]),
            "iat": int(token_info["expires_at"] - 3600)
        }
    
    # Check refresh tokens
    refresh_info = storage.refresh_tokens.get(token)
    if refresh_info:
        return {
            "active": True,
            "scope": " ".join(refresh_info["scopes"]),
            "client_id": refresh_info["client_id"],
            "username": refresh_info["user"],
            "token_type": "refresh_token"
        }
    
    # Token not found or invalid
    return {"active": False}

@mcp.tool()
def oauth_revoke(token: str, token_type_hint: Optional[str] = None) -> Dict[str, str]:
    """
    OAuth2 token revocation - revokes an access or refresh token
    
    Args:
        token: The token to revoke
        token_type_hint: Optional hint about token type
    """
    revoked = False
    
    # Try to revoke as access token
    if token in storage.access_tokens:
        del storage.access_tokens[token]
        revoked = True
    
    # Try to revoke as refresh token
    if token in storage.refresh_tokens:
        del storage.refresh_tokens[token]
        revoked = True
    
    if revoked:
        return {"status": "success", "message": "Token revoked"}
    else:
        return {"status": "success", "message": "Token not found (may already be revoked)"}

@mcp.tool()
def protected_resource(access_token: str, resource: str) -> Dict[str, Any]:
    """
    Access a protected resource using an OAuth2 access token
    
    Args:
        access_token: Bearer token for authorization
        resource: The resource to access
    """
    # Validate token
    token_info = storage.access_tokens.get(access_token)
    
    if not token_info:
        return {"error": "invalid_token", "error_description": "Invalid or expired token"}
    
    if time.time() > token_info["expires_at"]:
        return {"error": "invalid_token", "error_description": "Token expired"}
    
    # Check scopes for different resources
    if resource == "profile":
        if "profile" not in token_info["scopes"]:
            return {"error": "insufficient_scope", "error_description": "Requires 'profile' scope"}
        
        user = storage.users.get(token_info["user"])
        return {
            "username": token_info["user"],
            "email": user["email"] if user else None,
            "scopes": token_info["scopes"]
        }
    
    elif resource == "data":
        if "read" not in token_info["scopes"]:
            return {"error": "insufficient_scope", "error_description": "Requires 'read' scope"}
        
        return {
            "data": f"Secret data for {token_info['user'] or 'client'}",
            "timestamp": datetime.now().isoformat()
        }
    
    elif resource == "admin":
        if "admin" not in token_info["scopes"]:
            return {"error": "insufficient_scope", "error_description": "Requires 'admin' scope"}
        
        return {
            "total_users": len(storage.users),
            "total_clients": len(storage.clients),
            "active_tokens": len(storage.access_tokens),
            "active_refresh_tokens": len(storage.refresh_tokens)
        }
    
    else:
        return {"error": "not_found", "error_description": f"Resource '{resource}' not found"}

@mcp.tool()
def oauth_userinfo(access_token: str) -> Dict[str, Any]:
    """
    OpenID Connect UserInfo endpoint - returns user information
    
    Args:
        access_token: Bearer token with 'profile' scope
    """
    # Validate token
    token_info = storage.access_tokens.get(access_token)
    
    if not token_info:
        return {"error": "invalid_token", "error_description": "Invalid or expired token"}
    
    if time.time() > token_info["expires_at"]:
        return {"error": "invalid_token", "error_description": "Token expired"}
    
    if "profile" not in token_info["scopes"]:
        return {"error": "insufficient_scope", "error_description": "Requires 'profile' scope"}
    
    if not token_info["user"]:
        return {"error": "invalid_request", "error_description": "No user associated with token"}
    
    user = storage.users.get(token_info["user"])
    if not user:
        return {"error": "not_found", "error_description": "User not found"}
    
    return {
        "sub": token_info["user"],  # Subject identifier
        "email": user["email"],
        "email_verified": True,
        "name": token_info["user"].capitalize(),
        "preferred_username": token_info["user"],
        "updated_at": int(time.time())
    }

if __name__ == "__main__":
    print("OAuth2 Server with MCP")
    print("======================")
    print("\nAvailable users:")
    print("  - alice / password123 (scopes: read, write, profile)")
    print("  - admin / admin123 (scopes: read, write, profile, admin)")
    print("\nClient credentials:")
    print("  - client_id: demo-client-id")
    print("  - client_secret: demo-client-secret")
    print("\nTest the OAuth2 flow using the MCP tools!")
    
    mcp.run()