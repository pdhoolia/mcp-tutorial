# Standalone OAuth2 Provider Server
# This server handles authentication and token management
# It's completely separate from the MCP resource servers

import secrets
import time
import hashlib
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OAuth2Storage:
    """In-memory storage for OAuth2 data"""
    
    def __init__(self):
        # Registered OAuth clients (MCP servers can register here)
        self.clients = {
            "mcp-resource-server": {
                "client_secret": "mcp-server-secret",
                "redirect_uris": ["http://localhost:8081/callback"],
                "allowed_scopes": ["read", "write", "admin"],
                "name": "MCP Resource Server"
            },
            "test-client": {
                "client_secret": "test-secret",
                "redirect_uris": ["http://localhost:8082/callback"],
                "allowed_scopes": ["read", "write"],
                "name": "Test Client Application"
            }
        }
        
        # User accounts
        self.users = {
            "alice": {
                "password_hash": self._hash_password("password123"),
                "email": "alice@example.com",
                "full_name": "Alice Smith",
                "scopes": ["read", "write"]
            },
            "bob": {
                "password_hash": self._hash_password("secret456"),
                "email": "bob@example.com",
                "full_name": "Bob Johnson",
                "scopes": ["read"]
            },
            "admin": {
                "password_hash": self._hash_password("admin789"),
                "email": "admin@example.com",
                "full_name": "Admin User",
                "scopes": ["read", "write", "admin"]
            }
        }
        
        # Active tokens
        self.auth_codes = {}  # code -> {client_id, user, scopes, expires_at, redirect_uri}
        self.access_tokens = {}  # token -> {client_id, user, scopes, expires_at}
        self.refresh_tokens = {}  # token -> {client_id, user, scopes}
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        if not user:
            return False
        return user["password_hash"] == self._hash_password(password)

storage = OAuth2Storage()

class OAuth2Handler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 endpoints"""
    
    def log_message(self, format, *args):
        """Override to use logger instead of print"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/authorize":
            self.handle_authorize()
        elif parsed_path.path == "/login":
            self.show_login_form()
        elif parsed_path.path == "/.well-known/oauth-authorization-server":
            self.handle_metadata()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/token":
            self.handle_token()
        elif parsed_path.path == "/introspect":
            self.handle_introspect()
        elif parsed_path.path == "/revoke":
            self.handle_revoke()
        elif parsed_path.path == "/login":
            self.handle_login()
        else:
            self.send_error(404, "Not Found")
    
    def handle_metadata(self):
        """Return OAuth2 server metadata (RFC 8414)"""
        metadata = {
            "issuer": "http://localhost:9000",
            "authorization_endpoint": "http://localhost:9000/authorize",
            "token_endpoint": "http://localhost:9000/token",
            "introspection_endpoint": "http://localhost:9000/introspect",
            "revocation_endpoint": "http://localhost:9000/revoke",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "scopes_supported": ["read", "write", "admin"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"]
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(metadata).encode())
    
    def handle_authorize(self):
        """Handle authorization endpoint"""
        params = parse_qs(urlparse(self.path).query)
        
        client_id = params.get("client_id", [None])[0]
        redirect_uri = params.get("redirect_uri", [None])[0]
        response_type = params.get("response_type", [None])[0]
        scope = params.get("scope", [""])[0]
        state = params.get("state", [None])[0]
        
        # Validate client
        client = storage.clients.get(client_id)
        if not client:
            self.send_error(400, "Invalid client_id")
            return
        
        if redirect_uri not in client["redirect_uris"]:
            self.send_error(400, "Invalid redirect_uri")
            return
        
        if response_type != "code":
            self.send_error(400, "Unsupported response_type")
            return
        
        # Show login form (simplified - normally would validate scopes first)
        login_url = f"/login?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state or ''}"
        self.send_response(302)
        self.send_header("Location", login_url)
        self.end_headers()
    
    def show_login_form(self):
        """Display login form"""
        params = parse_qs(urlparse(self.path).query)
        
        html = """
        <html>
        <head>
            <title>OAuth2 Login</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                input { width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
                button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
                button:hover { background: #0056b3; }
                .info { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h2>OAuth2 Provider Login</h2>
            <div class="info">
                <strong>Test Accounts:</strong><br>
                alice / password123 (read, write)<br>
                bob / secret456 (read)<br>
                admin / admin789 (read, write, admin)
            </div>
            <form method="POST" action="/login">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="scope" value="{scope}">
                <input type="hidden" name="state" value="{state}">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """.format(
            client_id=params.get("client_id", [""])[0],
            redirect_uri=params.get("redirect_uri", [""])[0],
            scope=params.get("scope", [""])[0],
            state=params.get("state", [""])[0]
        )
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def handle_login(self):
        """Process login form submission"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode()
        params = parse_qs(post_data)
        
        username = params.get("username", [None])[0]
        password = params.get("password", [None])[0]
        client_id = params.get("client_id", [None])[0]
        redirect_uri = params.get("redirect_uri", [None])[0]
        scope = params.get("scope", [""])[0]
        state = params.get("state", [None])[0]
        
        # Verify credentials
        if not storage.verify_password(username, password):
            self.send_error(401, "Invalid credentials")
            return
        
        user = storage.users[username]
        requested_scopes = scope.split() if scope else []
        
        # Check user has requested scopes
        for s in requested_scopes:
            if s not in user["scopes"]:
                self.send_error(403, f"User lacks scope '{s}'")
                return
        
        # Generate authorization code
        code = secrets.token_urlsafe(32)
        storage.auth_codes[code] = {
            "client_id": client_id,
            "user": username,
            "scopes": requested_scopes,
            "expires_at": time.time() + 600,
            "redirect_uri": redirect_uri
        }
        
        # Redirect back to client
        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"
        
        self.send_response(302)
        self.send_header("Location", redirect_url)
        self.end_headers()
    
    def handle_token(self):
        """Handle token endpoint"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode()
        params = parse_qs(post_data)
        
        grant_type = params.get("grant_type", [None])[0]
        client_id = params.get("client_id", [None])[0]
        client_secret = params.get("client_secret", [None])[0]
        
        # Validate client
        client = storage.clients.get(client_id)
        if not client or client["client_secret"] != client_secret:
            self.send_json_error(401, "invalid_client", "Invalid client credentials")
            return
        
        if grant_type == "authorization_code":
            code = params.get("code", [None])[0]
            redirect_uri = params.get("redirect_uri", [None])[0]
            
            auth_info = storage.auth_codes.get(code)
            if not auth_info:
                self.send_json_error(400, "invalid_grant", "Invalid authorization code")
                return
            
            if time.time() > auth_info["expires_at"]:
                del storage.auth_codes[code]
                self.send_json_error(400, "invalid_grant", "Authorization code expired")
                return
            
            if auth_info["client_id"] != client_id:
                self.send_json_error(400, "invalid_grant", "Code issued to different client")
                return
            
            if redirect_uri != auth_info["redirect_uri"]:
                self.send_json_error(400, "invalid_grant", "Redirect URI mismatch")
                return
            
            # Generate tokens
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            
            storage.access_tokens[access_token] = {
                "client_id": client_id,
                "user": auth_info["user"],
                "scopes": auth_info["scopes"],
                "expires_at": time.time() + 3600
            }
            
            storage.refresh_tokens[refresh_token] = {
                "client_id": client_id,
                "user": auth_info["user"],
                "scopes": auth_info["scopes"]
            }
            
            del storage.auth_codes[code]
            
            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "scope": " ".join(auth_info["scopes"])
            }
            
        elif grant_type == "refresh_token":
            refresh_token = params.get("refresh_token", [None])[0]
            
            refresh_info = storage.refresh_tokens.get(refresh_token)
            if not refresh_info:
                self.send_json_error(400, "invalid_grant", "Invalid refresh token")
                return
            
            if refresh_info["client_id"] != client_id:
                self.send_json_error(400, "invalid_grant", "Token issued to different client")
                return
            
            # Generate new access token
            access_token = secrets.token_urlsafe(32)
            storage.access_tokens[access_token] = {
                "client_id": client_id,
                "user": refresh_info["user"],
                "scopes": refresh_info["scopes"],
                "expires_at": time.time() + 3600
            }
            
            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": " ".join(refresh_info["scopes"])
            }
            
        elif grant_type == "client_credentials":
            # Client credentials flow
            scope = params.get("scope", [""])[0]
            requested_scopes = scope.split() if scope else client["allowed_scopes"]
            
            for s in requested_scopes:
                if s not in client["allowed_scopes"]:
                    self.send_json_error(400, "invalid_scope", f"Scope '{s}' not allowed")
                    return
            
            access_token = secrets.token_urlsafe(32)
            storage.access_tokens[access_token] = {
                "client_id": client_id,
                "user": None,
                "scopes": requested_scopes,
                "expires_at": time.time() + 3600
            }
            
            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": " ".join(requested_scopes)
            }
        else:
            self.send_json_error(400, "unsupported_grant_type", f"Grant type '{grant_type}' not supported")
            return
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_introspect(self):
        """Handle token introspection (RFC 7662)"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode()
        params = parse_qs(post_data)
        
        token = params.get("token", [None])[0]
        
        # Check if it's an access token
        token_info = storage.access_tokens.get(token)
        if token_info:
            is_active = time.time() < token_info["expires_at"]
            response = {
                "active": is_active,
                "scope": " ".join(token_info["scopes"]),
                "client_id": token_info["client_id"],
                "username": token_info["user"],
                "token_type": "Bearer",
                "exp": int(token_info["expires_at"])
            }
        else:
            # Check refresh tokens
            refresh_info = storage.refresh_tokens.get(token)
            if refresh_info:
                response = {
                    "active": True,
                    "scope": " ".join(refresh_info["scopes"]),
                    "client_id": refresh_info["client_id"],
                    "username": refresh_info["user"],
                    "token_type": "refresh_token"
                }
            else:
                response = {"active": False}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def handle_revoke(self):
        """Handle token revocation (RFC 7009)"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode()
        params = parse_qs(post_data)
        
        token = params.get("token", [None])[0]
        
        # Revoke access token
        if token in storage.access_tokens:
            del storage.access_tokens[token]
        
        # Revoke refresh token
        if token in storage.refresh_tokens:
            del storage.refresh_tokens[token]
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status": "success"}')
    
    def send_json_error(self, status_code: int, error: str, description: str):
        """Send JSON error response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "error": error,
            "error_description": description
        }).encode())

def run_oauth_server(port: int = 9000):
    """Run the OAuth2 provider server"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, OAuth2Handler)
    
    print(f"OAuth2 Provider Server running on http://localhost:{port}")
    print("\nEndpoints:")
    print(f"  Authorization: http://localhost:{port}/authorize")
    print(f"  Token: http://localhost:{port}/token")
    print(f"  Introspection: http://localhost:{port}/introspect")
    print(f"  Revocation: http://localhost:{port}/revoke")
    print(f"  Metadata: http://localhost:{port}/.well-known/oauth-authorization-server")
    print("\nTest accounts:")
    print("  alice / password123 (scopes: read, write)")
    print("  bob / secret456 (scopes: read)")
    print("  admin / admin789 (scopes: read, write, admin)")
    print("\nRegistered clients:")
    print("  mcp-resource-server / mcp-server-secret")
    print("  test-client / test-secret")
    
    httpd.serve_forever()

if __name__ == "__main__":
    run_oauth_server()