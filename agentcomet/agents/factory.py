from typing import List, Optional
from .agent import Agent
from agentcomet.tools import ToolSpec

def create_agent(
    name: str,
    description: str = "",
    author: str = "",
    llm: Optional[str] = None,
    tools: Optional[List[ToolSpec]] = None,
    memory: bool = False
) -> Agent:
    """
    Declarative helper to create an Agent instance without subclassing.
    """
    class DynamicAgent(Agent):
        def setup(self):
            if llm:
                self.use_llm(llm)
            self.use_memory(memory)
            if tools:
                self.add_tools(*tools)
                
    return DynamicAgent(name=name, description=description, author=author)
