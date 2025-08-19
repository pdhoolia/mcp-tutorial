# OAuth2 client test script
# Demonstrates how to interact with the OAuth2 server
import asyncio
from mcp import ClientSession, StdioServerParameters, stdio_client
import json

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

async def test_oauth_flow():
    """Test the complete OAuth2 authorization code flow"""
    
    # Start the OAuth2 server in a separate terminal first:
    # uv run python learning/auth/2_oauth_flow/oauth_flow_demo_server.py
    
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "learning/06-auth/oauth/server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("OAuth2 Flow Test")
            print("=" * 50)
            
            # Step 1: Authorization request
            print("\n1. AUTHORIZATION REQUEST")
            print("-" * 30)
            auth_result = await session.call_tool(
            "oauth_authorize",
            arguments={
                "client_id": "demo-client-id",
                "redirect_uri": "http://localhost:8080/callback",
                "response_type": "code",
                "scope": "read write profile",
                "state": "random-state-123",
                "username": "alice",
                "password": "password123"
            }
            )
            auth_result = extract_tool_result(auth_result)
            print(f"Authorization result: {json.dumps(auth_result, indent=2)}")
            
            # Extract authorization code from redirect URL
            if "redirect_to" in auth_result:
                redirect_url = auth_result["redirect_to"]
                code = redirect_url.split("code=")[1].split("&")[0]
                print(f"\nAuthorization code: {code}")
                
                # Step 2: Token exchange
                print("\n2. TOKEN EXCHANGE")
                print("-" * 30)
                token_result = await session.call_tool(
                "oauth_token",
                arguments={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "http://localhost:8080/callback",
                    "client_id": "demo-client-id",
                    "client_secret": "demo-client-secret"
                }
                )
                token_result = extract_tool_result(token_result)
                print(f"Token result: {json.dumps(token_result, indent=2)}")
                
                if "access_token" in token_result:
                    access_token = token_result["access_token"]
                    refresh_token = token_result.get("refresh_token")
                    
                    # Step 3: Access protected resources
                    print("\n3. ACCESS PROTECTED RESOURCES")
                    print("-" * 30)
                    
                    # Get user profile
                    profile_result = await session.call_tool(
                    "protected_resource",
                    arguments={
                        "access_token": access_token,
                        "resource": "profile"
                    }
                    )
                    profile_result = extract_tool_result(profile_result)
                    print(f"Profile: {json.dumps(profile_result, indent=2)}")
                    
                    # Get user info (OpenID Connect)
                    userinfo_result = await session.call_tool(
                    "oauth_userinfo",
                    arguments={
                        "access_token": access_token
                    }
                    )
                    userinfo_result = extract_tool_result(userinfo_result)
                    print(f"UserInfo: {json.dumps(userinfo_result, indent=2)}")
                    
                    # Access data
                    data_result = await session.call_tool(
                    "protected_resource",
                    arguments={
                        "access_token": access_token,
                        "resource": "data"
                    }
                    )
                    data_result = extract_tool_result(data_result)
                    print(f"Data: {json.dumps(data_result, indent=2)}")
                    
                    # Try to access admin resource (should fail for alice)
                    admin_result = await session.call_tool(
                    "protected_resource",
                    arguments={
                        "access_token": access_token,
                        "resource": "admin"
                    }
                    )
                    admin_result = extract_tool_result(admin_result)
                    print(f"Admin (should fail): {json.dumps(admin_result, indent=2)}")
                    
                    # Step 4: Token introspection
                    print("\n4. TOKEN INTROSPECTION")
                    print("-" * 30)
                    introspect_result = await session.call_tool(
                    "oauth_introspect",
                    arguments={
                        "token": access_token
                    }
                    )
                    introspect_result = extract_tool_result(introspect_result)
                    print(f"Token info: {json.dumps(introspect_result, indent=2)}")
                    
                    # Step 5: Refresh token
                    if refresh_token:
                        print("\n5. REFRESH TOKEN")
                        print("-" * 30)
                        refresh_result = await session.call_tool(
                        "oauth_token",
                        arguments={
                            "grant_type": "refresh_token",
                            "refresh_token": refresh_token,
                            "client_id": "demo-client-id",
                            "client_secret": "demo-client-secret",
                            "scope": "read profile"  # Request subset of original scopes
                        }
                        )
                        refresh_result = extract_tool_result(refresh_result)
                        print(f"New token: {json.dumps(refresh_result, indent=2)}")
                    
                    # Step 6: Revoke token
                    print("\n6. REVOKE TOKEN")
                    print("-" * 30)
                    revoke_result = await session.call_tool(
                    "oauth_revoke",
                    arguments={
                        "token": access_token
                    }
                    )
                    revoke_result = extract_tool_result(revoke_result)
                    print(f"Revoke result: {json.dumps(revoke_result, indent=2)}")
                    
                    # Try to use revoked token
                    profile_after_revoke = await session.call_tool(
                    "protected_resource",
                    arguments={
                        "access_token": access_token,
                        "resource": "profile"
                    }
                    )
                    profile_after_revoke = extract_tool_result(profile_after_revoke)
                    print(f"After revoke (should fail): {json.dumps(profile_after_revoke, indent=2)}")
            
            # Test client credentials flow
            print("\n7. CLIENT CREDENTIALS FLOW")
            print("-" * 30)
            client_token_result = await session.call_tool(
            "oauth_token",
            arguments={
                "grant_type": "client_credentials",
                "client_id": "demo-client-id",
                "client_secret": "demo-client-secret",
                "scope": "read"
            }
            )
            client_token_result = extract_tool_result(client_token_result)
            print(f"Client token: {json.dumps(client_token_result, indent=2)}")
            
            if "access_token" in client_token_result:
                client_access_token = client_token_result["access_token"]
                
                # Access data with client token
                client_data_result = await session.call_tool(
                "protected_resource",
                arguments={
                    "access_token": client_access_token,
                    "resource": "data"
                }
                )
                client_data_result = extract_tool_result(client_data_result)
                print(f"Client data access: {json.dumps(client_data_result, indent=2)}")
            
            # Test with admin user
            print("\n8. ADMIN USER TEST")
            print("-" * 30)
            admin_auth_result = await session.call_tool(
            "oauth_authorize",
            arguments={
                "client_id": "demo-client-id",
                "redirect_uri": "http://localhost:8080/callback",
                "response_type": "code",
                "scope": "read write profile admin",
                "username": "admin",
                "password": "admin123"
            }
            )
            admin_auth_result = extract_tool_result(admin_auth_result)
            
            if "redirect_to" in admin_auth_result:
                admin_code = admin_auth_result["redirect_to"].split("code=")[1].split("&")[0]
                
                admin_token_result = await session.call_tool(
                "oauth_token",
                arguments={
                    "grant_type": "authorization_code",
                    "code": admin_code,
                    "redirect_uri": "http://localhost:8080/callback",
                    "client_id": "demo-client-id",
                    "client_secret": "demo-client-secret"
                }
                )
                admin_token_result = extract_tool_result(admin_token_result)
                
                if "access_token" in admin_token_result:
                    admin_access_token = admin_token_result["access_token"]
                    
                    # Access admin resource
                    admin_resource_result = await session.call_tool(
                    "protected_resource",
                    arguments={
                        "access_token": admin_access_token,
                        "resource": "admin"
                    }
                    )
                    admin_resource_result = extract_tool_result(admin_resource_result)
                    print(f"Admin resource (should succeed): {json.dumps(admin_resource_result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_oauth_flow())