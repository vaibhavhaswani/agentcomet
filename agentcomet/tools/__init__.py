from .core import tool, ToolSpec
from .registry import ToolRegistry
from .builtin.file_tools import read, write, list_dir

# Global default registry for builtin tools
default_registry = ToolRegistry()
default_registry.register_builtin(read)
default_registry.register_builtin(write)
default_registry.register_builtin(list_dir)

__all__ = ["tool", "ToolSpec", "ToolRegistry", "read", "write", "list_dir", "default_registry"]
