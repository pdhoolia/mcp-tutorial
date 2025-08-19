# Based on examples/snippets/servers/basic_prompt.py
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("Code Review Assistant")

@mcp.prompt(title="Review Python Code")
def review_python(code: str, focus_area: str = "general") -> list[base.Message]:
    """Generate a code review prompt for Python code"""
    
    focus_prompts = {
        "general": "Focus on code quality, readability, and best practices.",
        "performance": "Focus on performance optimizations and efficiency.",
        "security": "Focus on security vulnerabilities and safety.",
        "testing": "Focus on testability and suggest test cases."
    }
    
    return [
        base.UserMessage(f"Please review this Python code:\n\n```python\n{code}\n```"),
        base.AssistantMessage("I'll review this code for you."),
        base.UserMessage(focus_prompts.get(focus_area, focus_prompts["general"]))
    ]

@mcp.prompt(title="Debug Error")
def debug_error(error_message: str, code_context: str = "") -> str:
    """Generate a debugging prompt for an error"""
    prompt = f"I'm encountering this error:\n\n{error_message}"
    
    if code_context:
        prompt += f"\n\nHere's the relevant code:\n```python\n{code_context}\n```"
    
    prompt += "\n\nCan you help me understand what's causing this and how to fix it?"
    return prompt

@mcp.prompt(title="Explain Code")
def explain_code(code: str, audience: str = "developer") -> list[base.Message]:
    """Generate prompts to explain code to different audiences"""
    
    audience_intros = {
        "beginner": "Explain this code in simple terms, as if to someone new to programming:",
        "developer": "Explain what this code does and its key design decisions:",
        "reviewer": "Provide a technical analysis of this code's architecture and patterns:"
    }
    
    return [
        base.UserMessage(audience_intros.get(audience, audience_intros["developer"])),
        base.UserMessage(f"```python\n{code}\n```")
    ]

if __name__ == "__main__":
    mcp.run()