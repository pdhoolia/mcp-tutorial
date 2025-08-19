# Based on examples/snippets/servers/basic_resource.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator with History")

# In-memory storage for calculation history
calculation_history: list[str] = []

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return calculate(f"{a} + {b}")

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return calculate(f"{a} * {b}")

@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return calculate(f"{a} / {b}")

@mcp.tool()
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression"""
    result = eval(expression)  # Note: In production, use a safe parser!
    calculation_history.append(f"{expression} = {result}")
    return result

@mcp.resource("history://recent")
def get_recent_history() -> str:
    """Get recent calculation history"""
    if not calculation_history:
        return "No calculations yet"
    return "\n".join(calculation_history[-10:])  # Last 10 calculations

@mcp.resource("history://all")
def get_all_history() -> str:
    """Get all calculation history"""
    if not calculation_history:
        return "No calculations yet"
    return "\n".join(calculation_history)

if __name__ == "__main__":
    mcp.run()