from .core import tool, ToolSpec
from .registry import ToolRegistry
from .builtin.file_tools import read, write

# Global default registry for builtin tools
default_registry = ToolRegistry()
default_registry.register_builtin(read)
default_registry.register_builtin(write)

__all__ = ["tool", "ToolSpec", "ToolRegistry", "read", "write", "default_registry"]
