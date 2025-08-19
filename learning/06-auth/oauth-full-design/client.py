# Client application that authenticates with OAuth provider and accesses MCP resources
# Demonstrates the complete flow with separate OAuth and resource servers

import asyncio
import httpx
from mcp import stdio_client, StdioServerParameters
from urllib.parse import urlencode
import secrets
import json

# Configuration
OAUTH_PROVIDER_URL = "http://localhost:9000"
MCP_RESOURCE_SERVER_COMMAND = ["uv", "run", "python", "learning/06-auth/oauth-full-design/mcp_resource_server.py"]

class OAuthClient:
    """OAuth client for authentication flow"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.state = secrets.token_urlsafe(16)
    
    async def get_authorization_code(self, username: str, password: str, scopes: list) -> str:
        """
        Simulate authorization code flow (normally would open browser)
        For demo purposes, we'll directly post to the login endpoint
        """
        async with httpx.AsyncClient() as client:
            # Step 1: Get authorization URL
            auth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "state": self.state
            }
            auth_url = f"{OAUTH_PROVIDER_URL}/authorize?" + urlencode(auth_params)
            
            print(f"\nAuthorization URL: {auth_url}")
            print(f"Simulating login with user: {username}")
            
            # Step 2: Simulate login (normally user would do this in browser)
            login_data = {
                "username": username,
                "password": password,
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(scopes),
                "state": self.state
            }
            
            response = await client.post(
                f"{OAUTH_PROVIDER_URL}/login",
                data=login_data,
                follow_redirects=False
            )
            
            if response.status_code != 302:
                raise Exception(f"Login failed: {response.text}")
            
            # Extract code from redirect
            location = response.headers.get("location")
            if not location:
                raise Exception("No redirect location")
            
            # Parse authorization code from redirect URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(location)
            params = parse_qs(parsed.query)
            
            if "code" not in params:
                raise Exception(f"No authorization code in redirect: {location}")
            
            return params["code"][0]
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = await client.post(
                f"{OAUTH_PROVIDER_URL}/token",
                data=token_data
            )
            
            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")
            
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """Use refresh token to get new access token"""
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = await client.post(
                f"{OAUTH_PROVIDER_URL}/token",
                data=token_data
            )
            
            if response.status_code != 200:
                raise Exception(f"Token refresh failed: {response.text}")
            
            return response.json()

def extract_tool_result(result):
    """Extract the actual content from a tool result"""
    if hasattr(result, 'content'):
        # content is a list of content items
        for item in result.content:
            if hasattr(item, 'text'):
                # The text might already be a dict/str or needs JSON parsing
                text = item.text
                if isinstance(text, dict):
                    return text
                elif isinstance(text, str):
                    if text.strip():  # Only parse if not empty
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            # Text is not JSON, return as is
                            return text
                    else:
                        return {}
        return result.content
    return result

async def test_full_flow():
    """Test the complete OAuth flow with separate servers"""
    
    print("Full OAuth + MCP Integration Test")
    print("=" * 60)
    print("\nMake sure the OAuth provider is running:")
    print("  uv run python learning/06-auth/oauth-full-design/oauth_provider.py")
    print("\nPress Enter to continue...")
    input()

    # Initialize OAuth client
    oauth_client = OAuthClient(
        client_id="test-client",
        client_secret="test-secret",
        redirect_uri="http://localhost:8082/callback"
    )
    
    # Test with different users
    test_cases = [
        {
            "user": "alice",
            "password": "password123",
            "scopes": ["read", "write"],
            "test_operations": ["read", "write"]
        },
        {
            "user": "bob",
            "password": "secret456",
            "scopes": ["read"],
            "test_operations": ["read"]
        },
        {
            "user": "admin",
            "password": "admin789",
            "scopes": ["read", "write", "admin"],
            "test_operations": ["read", "write", "admin"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Testing with user: {test_case['user']}")
        print(f"Requested scopes: {test_case['scopes']}")
        print("=" * 60)
        
        try:
            # Get authorization code
            print("\n1. Getting authorization code...")
            code = await oauth_client.get_authorization_code(
                test_case["user"],
                test_case["password"],
                test_case["scopes"]
            )
            print(f"   Authorization code: {code[:10]}...")
            
            # Exchange for token
            print("\n2. Exchanging code for token...")
            token_response = await oauth_client.exchange_code_for_token(code)
            access_token = token_response["access_token"]
            refresh_token = token_response.get("refresh_token")
            print(f"   Access token: {access_token[:10]}...")
            print(f"   Token type: {token_response.get('token_type')}")
            print(f"   Expires in: {token_response.get('expires_in')} seconds")
            print(f"   Scopes: {token_response.get('scope')}")
            
            # Connect to MCP resource server
            print("\n3. Connecting to MCP resource server...")

            server_params = StdioServerParameters(
                command=MCP_RESOURCE_SERVER_COMMAND[0],
                args=MCP_RESOURCE_SERVER_COMMAND[1:]
            )
            
            async with stdio_client(server_params) as (read, write):
                from mcp import ClientSession
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Test public endpoint
                    print("\n4. Testing public endpoint...")
                    public_result = await session.call_tool("public_info", arguments={})
                    public_info = extract_tool_result(public_result)
                    print(f"   Public info: {json.dumps(public_info, indent=2)}")
                    
                    # Get user profile
                    print("\n5. Getting user profile...")
                    profile_result = await session.call_tool(
                        "get_user_profile",
                        arguments={"token": access_token}
                    )
                    profile = extract_tool_result(profile_result)
                    print(f"   Profile: {json.dumps(profile, indent=2)}")
                    
                    # List available resources
                    print("\n6. Listing available resources...")
                    resources_result = await session.call_tool(
                        "list_available_resources",
                        arguments={"token": access_token}
                    )
                    resources = extract_tool_result(resources_result)
                    print(f"   Available: {json.dumps(resources, indent=2)}")
                    
                    # Test operations based on scopes
                    if "read" in test_case["test_operations"]:
                        print("\n7. Testing READ operation...")
                        try:
                            read_result = await session.call_tool(
                                "read_data",
                                arguments={
                                    "token": access_token,
                                    "resource_id": "doc1"
                                }
                            )
                            read_data = extract_tool_result(read_result)
                            print(f"   Read result: {json.dumps(read_data, indent=2)}")
                        except Exception as e:
                            print(f"   Read failed: {e}")
                    
                    if "write" in test_case["test_operations"]:
                        print("\n8. Testing WRITE operation...")
                        try:
                            write_result = await session.call_tool(
                                "write_data",
                                arguments={
                                    "token": access_token,
                                    "resource_id": "new_doc",
                                    "content": f"Content created by {test_case['user']}"
                                }
                            )
                            write_data = extract_tool_result(write_result)
                            print(f"   Write result: {json.dumps(write_data, indent=2)}")
                        except Exception as e:
                            print(f"   Write failed: {e}")
                    
                    if "admin" in test_case["test_operations"]:
                        print("\n9. Testing ADMIN operation...")
                        try:
                            admin_result = await session.call_tool(
                                "admin_operation",
                                arguments={
                                    "token": access_token,
                                    "operation": "system_status"
                                }
                            )
                            admin_data = extract_tool_result(admin_result)
                            print(f"   Admin result: {json.dumps(admin_data, indent=2)}")
                        except Exception as e:
                            print(f"   Admin operation failed: {e}")
                    
                    # Test unauthorized operation
                    print("\n10. Testing unauthorized operation (should fail)...")
                    if "admin" not in test_case["test_operations"]:
                        try:
                            admin_result = await session.call_tool(
                                "admin_operation",
                                arguments={
                                    "token": access_token,
                                    "operation": "list_users"
                                }
                            )
                            admin_data = extract_tool_result(admin_result)
                            print(f"   Unexpected success: {admin_data}")
                        except Exception as e:
                            print(f"   Expected failure: {e}")
                    
                    # Test token refresh if we have a refresh token
                    if refresh_token:
                        print("\n11. Testing token refresh...")
                        new_token_response = await oauth_client.refresh_token(refresh_token)
                        new_access_token = new_token_response["access_token"]
                        print(f"   New access token: {new_access_token[:10]}...")
                        
                        # Use new token
                        profile_result = await session.call_tool(
                            "get_user_profile",
                            arguments={"token": new_access_token}
                        )
                        profile = extract_tool_result(profile_result)
                        print(f"   Profile with new token: {json.dumps(profile, indent=2)}")
        
        except Exception as e:
            import traceback
            print(f"\nError during test: {e}")
            print(f"Error type: {type(e).__name__}")
            
            # Handle ExceptionGroup specifically
            if hasattr(e, 'exceptions'):
                print(f"ExceptionGroup contains {len(e.exceptions)} exception(s):")
                for i, exc in enumerate(e.exceptions):
                    print(f"\nException {i+1}: {exc}")
                    print(f"Type: {type(exc).__name__}")
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
            else:
                print("Traceback:")
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_full_flow())