import os
from agentcomet.tools import tool

@tool
def read(path: str) -> str:
    """Read contents of a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@tool
def write(path: str, content: str) -> str:
    """Write content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return "File written"

# Future builtin tools can go here (e.g., execute, web_search, etc.)
