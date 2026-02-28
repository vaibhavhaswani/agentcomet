from typing import Dict, List, Optional
from .core import ToolSpec

class ToolRegistry:
    """Registry to manage and resolve builtin, custom, and agent-attached tools."""
    
    def __init__(self):
        self.builtin_tools: Dict[str, ToolSpec] = {}
        self.custom_tools: Dict[str, ToolSpec] = {}
        self.agent_tools: Dict[str, ToolSpec] = {}
        
    def register_builtin(self, tool: ToolSpec):
        """Register a core framework tool."""
        self.builtin_tools[tool.name] = tool
        
    def register_custom(self, tool: ToolSpec):
        """Register a user-provided custom tool."""
        self.custom_tools[tool.name] = tool
        
    def register_agent_tool(self, tool: ToolSpec):
        """Register a tool specific to an agent instance."""
        self.agent_tools[tool.name] = tool
        
    def resolve(self, name: str) -> Optional[ToolSpec]:
        """Resolve a tool by name, checking agent -> custom -> builtin."""
        if name in self.agent_tools:
            return self.agent_tools[name]
        if name in self.custom_tools:
            return self.custom_tools[name]
        if name in self.builtin_tools:
            return self.builtin_tools[name]
        return None

    def get_all_tools(self) -> List[ToolSpec]:
        """Return all available tools."""
        all_tools = {}
        # Order dictates override priority
        all_tools.update(self.builtin_tools)
        all_tools.update(self.custom_tools)
        all_tools.update(self.agent_tools)
        return list(all_tools.values())
