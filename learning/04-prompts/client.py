# Client example demonstrating idiomatic usage of MCP prompts
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demonstrate_prompts():
    """
    Demonstrates how MCP prompts are designed to be used by clients.
    
    Key concepts:
    1. Prompts are discovered dynamically from the server
    2. Clients retrieve prompt templates with parameters
    3. Prompts generate messages/text that can be sent to LLMs
    4. The client controls how to use the generated prompt content
    """
    
    # Connect to the Code Review Assistant server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "learning/04-prompts/server.py", "stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            print("Connected to Code Review Assistant\n")
            
            # 1. DISCOVER AVAILABLE PROMPTS
            print("=" * 60)
            print("1. DISCOVERING AVAILABLE PROMPTS")
            print("=" * 60)
            
            prompts_response = await session.list_prompts()
            available_prompts = prompts_response.prompts
            
            print(f"Found {len(available_prompts)} prompts:")
            for prompt in available_prompts:
                print(f"  - {prompt.name}: {prompt.description}")
                if prompt.arguments:
                    print("    Parameters:")
                    for arg in prompt.arguments:
                        required = "required" if arg.required else "optional"
                        print(f"      • {arg.name} ({required}): {arg.description}")
            
            # 2. USE THE "REVIEW PYTHON CODE" PROMPT
            print("\n" + "=" * 60)
            print("2. USING 'REVIEW PYTHON CODE' PROMPT")
            print("=" * 60)
            
            # Sample code to review
            sample_code = """
def calculate_fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib
"""
            
            # Get the prompt with different focus areas
            focus_areas = ["general", "performance", "testing"]
            
            for focus in focus_areas:
                print(f"\n--- Focus: {focus.upper()} ---")
                
                # Get the prompt template
                prompt_result = await session.get_prompt(
                    "review_python",
                    arguments={
                        "code": sample_code,
                        "focus_area": focus
                    }
                )
                
                # Display the generated prompt messages
                print("Generated prompt messages:")
                for i, message in enumerate(prompt_result.messages, 1):
                    role = message.role
                    content = message.content.text if hasattr(message.content, 'text') else str(message.content)
                    # Truncate long content for display
                    if len(content) > 100:
                        content = content[:100] + "..."
                    print(f"  Message {i} ({role}): {content}")
            
            # 3. USE THE "DEBUG ERROR" PROMPT
            print("\n" + "=" * 60)
            print("3. USING 'DEBUG ERROR' PROMPT")
            print("=" * 60)
            
            error_examples = [
                {
                    "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
                    "code_context": "result = 5 + '10'"
                },
                {
                    "error_message": "IndexError: list index out of range",
                    "code_context": ""  # No context provided
                }
            ]
            
            for example in error_examples:
                print(f"\nError: {example['error_message'][:50]}...")
                
                # Get the debugging prompt
                prompt_result = await session.get_prompt(
                    "debug_error",
                    arguments=example
                )
                
                # For debug_error, the result is a string
                prompt_text = prompt_result.messages[0].content.text
                print(f"Generated prompt (first 150 chars):")
                print(f"  {prompt_text[:150]}...")
            
            # 4. USE THE "EXPLAIN CODE" PROMPT FOR DIFFERENT AUDIENCES
            print("\n" + "=" * 60)
            print("4. USING 'EXPLAIN CODE' PROMPT FOR DIFFERENT AUDIENCES")
            print("=" * 60)
            
            explanation_code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
            
            audiences = ["beginner", "developer", "reviewer"]
            
            for audience in audiences:
                print(f"\n--- Audience: {audience.upper()} ---")
                
                # Get the explanation prompt
                prompt_result = await session.get_prompt(
                    "explain_code",
                    arguments={
                        "code": explanation_code,
                        "audience": audience
                    }
                )
                
                # Show the tailored introduction
                intro_message = prompt_result.messages[0]
                print(f"Tailored introduction:")
                print(f"  {intro_message.content.text}")
            
            # 5. DEMONSTRATE ERROR HANDLING
            print("\n" + "=" * 60)
            print("5. ERROR HANDLING")
            print("=" * 60)
            
            try:
                # Try to get a non-existent prompt
                await session.get_prompt("non_existent_prompt", {})
            except Exception as e:
                print(f"Expected error for non-existent prompt: {e}")
            
            try:
                # Try to get a prompt with missing required parameters
                await session.get_prompt("review_python", {})  # Missing 'code' parameter
            except Exception as e:
                print(f"Expected error for missing parameters: {e}")
            
            print("\n" + "=" * 60)
            print("DEMONSTRATION COMPLETE")
            print("=" * 60)

if __name__ == "__main__":
    print("MCP Prompts Client Example")
    print("This demonstrates the idiomatic usage of MCP prompts\n")
    
    asyncio.run(demonstrate_prompts())