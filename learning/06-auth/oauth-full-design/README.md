# Full OAuth2 + MCP Integration

This example demonstrates a complete, production-like architecture where authentication is fully separated from resource servers using OAuth2.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client    │────▶│  OAuth Provider  │◀────│ MCP Resource    │
│ Application │     │   (Port 9000)    │     │    Server       │
└─────────────┘     └──────────────────┘     └─────────────────┘
      │                                              │
      │                                              │
      └──────────────────────────────────────────────┘
         Direct communication with MCP tools
```

### Components

1. **OAuth Provider Server** ([`oauth_provider.py`](oauth_provider.py) - Port 9000)
   - Standalone OAuth2 authorization server
   - Handles user authentication
   - Issues and validates tokens
   - Provides token introspection for resource servers
   - Can be replaced with Auth0, Okta, Keycloak, etc.

2. **MCP Resource Server** ([`mcp_resource_server.py`](mcp_resource_server.py))
   - Provides protected MCP tools/resources
   - Validates tokens with OAuth provider via introspection
   - Enforces scope-based access control
   - Caches token validation for performance

3. **Client Application** ([`client.py`](client.py))
   - Authenticates users via OAuth provider
   - Obtains access tokens
   - Calls protected MCP tools with tokens
   - Handles token refresh

## OAuth2 Flow

1. **Authorization**: Client redirects user to OAuth provider
2. **Authentication**: User logs in at OAuth provider
3. **Authorization Code**: OAuth provider redirects back with code
4. **Token Exchange**: Client exchanges code for access token
5. **Resource Access**: Client uses token to access MCP resources
6. **Token Validation**: MCP server validates token with OAuth provider
7. **Response**: MCP server returns protected data

## Running the Example

### Step 1: Start the OAuth Provider

```bash
uv run python learning/06-auth/oauth-full-design/oauth_provider.py
```

The OAuth provider will run on http://localhost:9000

### Step 2: Run the Test Client

In a new terminal:

```bash
uv run python learning/06-auth/oauth-full-design/client.py
```

The client will:
- Authenticate with the OAuth provider
- Get access tokens
- Connect to the MCP resource server
- Access protected resources based on scopes

## Test Accounts

| Username | Password     | Scopes                |
|----------|-------------|-----------------------|
| alice    | password123 | read, write           |
| bob      | secret456   | read                  |
| admin    | admin789    | read, write, admin    |

## OAuth Endpoints

### OAuth Provider (Port 9000)

- `GET /authorize` - Authorization endpoint
- `POST /token` - Token endpoint
- `POST /introspect` - Token introspection (RFC 7662)
- `POST /revoke` - Token revocation (RFC 7009)
- `GET /.well-known/oauth-authorization-server` - Server metadata (RFC 8414)

### MCP Resource Server

Protected tools requiring authentication:
- `get_user_profile` - Get current user info (any valid token)
- `read_data` - Read protected data (requires 'read' scope)
- `write_data` - Write protected data (requires 'write' scope)
- `admin_operation` - Admin operations (requires 'admin' scope)
- `list_available_resources` - List accessible resources

Public tools (no auth required):
- `public_info` - Get server information

## Security Features

1. **Token Validation**: Every request is validated with the OAuth provider
2. **Scope Enforcement**: Operations require specific scopes
3. **Token Caching**: Reduces introspection calls while maintaining security
4. **User Context**: Operations receive user identity from validated tokens
5. **Token Expiration**: Access tokens expire after 1 hour
6. **Refresh Tokens**: Long-lived tokens for getting new access tokens

## Scope-Based Access Control

| Scope | Permissions |
|-------|-------------|
| read  | Read data and documents |
| write | Create and modify data |
| admin | System administration, user management |

## Production Considerations

This example is simplified for demonstration. In production:

1. **Use HTTPS** everywhere
2. **Implement PKCE** for public clients
3. **Use secure token storage** (not in-memory)
4. **Add rate limiting** on all endpoints
5. **Implement proper CSRF protection**
6. **Use production OAuth provider** (Auth0, Okta, Keycloak)
7. **Add comprehensive logging and monitoring**
8. **Implement token rotation strategies**
9. **Use asymmetric keys** for token signing/validation
10. **Add consent screens** for scope approval

## Replacing with Enterprise OAuth Providers

The OAuth provider in this example can be replaced with:

- **Auth0**: Change `OAUTH_PROVIDER_URL` and configure application
- **Okta**: Update endpoints and add Okta SDK
- **Keycloak**: Point to Keycloak realm endpoints
- **Azure AD**: Use Microsoft identity platform endpoints
- **Google OAuth**: Configure Google Cloud Console application

The MCP resource server only needs the introspection endpoint URL to work with any standard OAuth2 provider.

## Token Introspection

The resource server validates tokens using RFC 7662 token introspection:

```json
POST /introspect
Content-Type: application/x-www-form-urlencoded

token=<access_token>
```

Response:
```json
{
  "active": true,
  "scope": "read write",
  "client_id": "test-client",
  "username": "alice",
  "token_type": "Bearer",
  "exp": 1234567890
}
```

This allows the resource server to validate tokens without sharing secrets or maintaining user databases.