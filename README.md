# MCP Foundations: Practical Learning Series with Python SDK

This learning series uses **hands-on examples** adapted from the `python-sdk` repository.

## Prerequisites Setup

```bash
# Clone the repository
git clone https://github.ibm.com/pdhoolia/mcp-tutorial.git
cd mcp-tutorial

# Create virtual environment using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
uv sync --all-extras --dev
```

## Module 1: Hello World

### Learning Objectives
- Understand MCP client-server architecture
- Build and run your first MCP server
- Test servers using MCP Inspector

### Hands-on Exercise 1: Your First MCP Server

**File:** [`learning/01-hello-world/server.py`](learning/01-hello-world/server.py)

**Running & testing with MCP Inspector**  
```bash
# simplified command because of `uv pip install 'mcp[cli]'`
uv run mcp dev learning/01-hello-world/server.py

# without the cli
# npx @modelcontextprotocol/inspector uv run python learning/01-hello-world/server.py stdio
```

### Exercise 2: Adding Resources

**File:** [`learning/01-hello-world/server_with_resources.py`](learning/01-hello-world/server_with_resources.py)

Let's run & debug in a similar manner as before.

## Module 2: Client-Server Communication

### Learning Objectives
- Build MCP clients
- Understand request-response patterns
- Handle tool calls programmatically

### Exercise 1: Building a Simple Client

**File:** [`learning/02-mcp-client/client.py`](learning/02-mcp-client/client.py)

**Running:**  

```bash
uv run python learning/02-mcp-client/client.py
```

### Exercise 2: Interactive Client

**File:** [`learning/02-mcp-client/interactive_client.py`](learning/02-mcp-client/interactive_client.py)

**Running:**  

```bash
uv run python learning/02-mcp-client/interactive_client.py
```

## Module 3: Output Schema

### Learning Objectives
- Use Pydantic models for structured data
- See that MCP server tool listing now returns tool output schema as well
- Implement type validation
- Return complex data structures

### Exercise: Weather Service with Structured Output

**File:** [`learning/03-output-schema/server.py`](learning/03-output-schema/server.py)

**Testing with client:**

**File:** [`learning/03-output-schema/client.py`](learning/03-output-schema/client.py)

**Test with MCP Inspector**  
```bash
uv run mcp dev learning/03-output-schema/server.py
```

## Module 4: Prompts & Templates

### Learning Objectives
- Create reusable prompt templates
- Build context-aware prompts
- Implement prompt parameters
- Implement a client to understand how the MCP prompts are designed to be used by clients

### Exercise: Code Review Assistant

**File:** [`learning/04-prompts/server.py`](learning/04-prompts/server.py)

### Exercise: Prompts Client

**File:** [`learning/04-prompts/client.py`](learning/04-prompts/client.py)

In a real application, the workflow would be:

1. Client discovers available prompts from the server
2. User selects a suitable prompt and provides necessary parameters
3. Client retrieves the formatted prompt from the server
4. Client sends the prompt to an LLM (Claude, GPT, etc.)
5. LLM response is shown to the user or processed further

Example pseudo-code:
```python
# Get prompt from MCP server
prompt_result = await session.get_prompt("review_python", {
    "code": user_code,
    "focus_area": "security"
})

# Send to LLM (example with hypothetical LLM client)
llm_response = await llm_client.send_messages(prompt_result.messages)

# Display or process the LLM's response
print(f"Code review results: {llm_response}")
```

Key Takeaways:
* Prompts are templates that generate consistent, well-structured messages
* Parameters allow customization (code, focus areas, audiences, etc.)
* Prompts return messages/text ready to be sent to LLMs
* The client maintains control over how prompts are used
* This pattern enables reusable, maintainable prompt engineering

## Module 5: Transport Protocols

### Learning Objectives
- Understand stdio vs HTTP transports
- Implement HTTP-based MCP servers
- Handle multiple transport types

### Exercise: Server with SSE transport

**File:** [`learning/05-transports/server.py`](learning/05-transports/server.py)

**Run MCP server (with SSE transport):**

```bash
# Start the server with SSE transport
uv run python learning/05-transports/server.py sse
```

**Test using a python client:**

**File:** [`learning/05-transports/client_sse.py`](learning/05-transports/client_sse.py)

```bash
uv run python learning/05-transports/client_sse.py
```

**Test using API client:**

**File:** [`learning/05-transports/client_sse.http`](learning/05-transports/client_sse.http)

### Exercise: Server with Streamable-http transport

**Run MCP server (with streamable-http transport):**

```bash
# Start the server
uv run python learning/05-transports/server.py streamable-http
```

**Test using API client:**

**File:** [`learning/05-transports/client_streamable.http`](learning/05-transports/client_streamable.http)


## Module 6: Authentication & Security

### Learning Objectives
- Basics of authorization
- Basics of oauth
- Securing mcp resources with oauth

### Exercise: Basics of authorization

**File:** [`learning/06-auth/basic-design/server.py`](learning/06-auth/basic-design/server.py)

**Test with MCP Inspector**  
```bash
uv run mcp dev learning/06-auth/basic-design/server.py
```

### Exercise: Basics of oauth

This MCP server implements a both the auth-provider, and the resource-server in a single combined implementation.

**File:** [`learning/06-auth/oauth/server.py`](learning/06-auth/oauth/server.py)
**File:** [`learning/06-auth/oauth/client.py`](learning/06-auth/oauth/client.py)

**Test with MCP Inspector** 

```bash
uv run mcp dev learning/06-auth/oauth/server.py
```

**Experience the oauth sequence**
- **`oauth_authorize`**: login to at OAuth provider to get the code
    - client_id: demo-client-id
    - redirect_uri: http://localhost:8080/callback
    - response_type: code
    - scope: read write profile
    - state: random-state-123
    - username: alice
    - password: password123
- **`oauth_token`**: Exchange the code for access token
    - grant_type: authorization_code,
    - code: `<code>` from the response of the previous call,
    - redirect_uri: http://localhost:8080/callback,
    - client_id: demo-client-id,
    - client_secret: demo-client-secret
- **`protected_resource`**: Use `<token>` to access protected MCP resources
    - access_token: `<token>` from the response of the previous step
    - resource: `profile | data | admin`, alice's token shouldn't have access to `admin`

**Test the whole sequence with a python based MCP client**  
```bash
uv run python learning/06-auth/oauth/client.py
```

### Exercise: Full blown oauth example with separate oauth provider and mcp resource servers

This is how in practice we'll have things.

- **File:** [`learning/06-auth/oauth-full-design/oauth_provider.py`](learning/06-auth/oauth-full-design/oauth_provider.py)
- **File:** [`learning/06-auth/oauth-full-design/mcp_resource_server.py`](learning/06-auth/oauth-full-design/mcp_resource_server.py)
- **File:** [`learning/06-auth/oauth-full-design/client.py`](learning/06-auth/oauth-full-design/client.py)

[**This README**](learning/06-auth/oauth-full-design/README.md) provides more details.

## Module 7: Pytest

### Learning Objectives
- How to write pytests for MCP servers

### Exercise: Testing MCP Tools

**File:** [`learning/07-pytest/test_calculator_server.py`](learning/07-pytest/test_calculator_server.py)

- `create_connected_server_and_client_session`: Use this test utility from the MCP python-sdk that creates a connected pair of server and client sessions for testing MCP servers without network overhead. This pattern allows testing MCP servers without needing actual network connections or separate processes for server and client.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run --frozen pytest learning/07-pytest/test_calculator_server.py
# - PYTEST_DISABLE_PLUGIN_AUTOLOAD="" - Disables automatic loading of pytest plugins, ensuring a clean test environment without interference from third-party plugins
# - uv run --frozen - Executes the command using uv (a fast Python package manager) with --frozen flag, which uses exact dependency versions from the lockfile without updating them
```

## Module 8: Real-World Integrations

### Learning Objective
- Build a capstone MCP Server
- Integrate it into Generalist Assistants
- Integrate it into IDEs
- Patterns of integration into Agentic Frameworks like LangGraph

### Understand Capstone Project: Task Management System

- Understand the tools in [Task Management MCP Server](learning/08-integrations/server.py)
- Run the server:
    ```bash
    uv run python learning/08-integrations/server.py streamable-http
    ```
- Understand the [Python Client](learning/08-integrations/client.py) that will seed some tasks using the `create_task` tool
- Run the client:
    ```bash
    uv run python learning/08-integrations/client.py
    ```
- Try using the mcp inspector
    ```bash
    uv run mcp dev learning/08-integrations/server.py
    ```
    - list and then try the resource: `get_task_summary`
    - list and then try the `create_task` tool (give the new task some unique tag like `demo`)
    - note the `task_id` generated for the new task
    - try the `update_task_status` tool to update status to `in_progress`
    - try the `list_tasks` (filter using the `demo` tag)
- You may also try using the [REST Client](learning/08-integrations/client.http)

### Integrate into Claude

- Use the mcp cli to add our server to Claude
    ```bash
    uv run mcp install learning/08-integrations/server.py
    ```

- OR Add to `~/Library/Application Support/Claude/claude_desktop_config.json` the following
    ```json
    {
    "mcpServers": {
        "task-manager": {
        "command": "uv",
        "args": ["run", "python", "/Users/pdhoolia/ghe/mcp-tutorial/learning/08-integrations/server.py", "stdio"]
        }
    }
    }
    ```

### Integrate into VS Code

Let's assume you have access to GitHub-Copilot

- CMD+SHIFT-P > MCP: Add Server
- Let's pick > Command stdio ...Manual Install
- In the Command to run (with optional arguments) > `uv run python /Users/pdhoolia/ghe/mcp-tutorial/learning/08-integrations/server.py`
- Let's name it `task-manager`
- Open Copilot Chat
- Click on the `Configure tools` icon and ensure that there is a selected entry for `MCP Servers: task-manager`
- Give a try to creating, updating, and listing tasks

### Using MCP Servers with LangGraph

Most agent frameworks have out of the box support for using tools from MCP servers.
Here's an example of a langgraph agent using the [calculator server from module 01-hello-world](learning/01-hello-world/server_with_resources.py), and the [weather server from module 05-transports](learning/05-transports/server.py): [learning/08-integrations/langgraph_agent.py](learning/08-integrations/langgraph_agent.py)

**To run:**

Create a `.env` file with:
```python
OPENWEATHER_API_KEY=304bcf44d4823d79049378809f39088d
OPENAI_API_KEY=<your-openai-api-key>
```

And then run:
```bash
uv run python learning/08-integrations/langgraph_agent.py  
```

You should see the responses to the 2 questions being asked.


## Additional Resources

### Documentation
- [MCP Specification](https://modelcontextprotocol.io/docs)
- [Python SDK Docs](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Python SDK Examples](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples)
- [Using MCP with LangGraph](https://langchain-ai.github.io/langgraph/agents/mcp/)
