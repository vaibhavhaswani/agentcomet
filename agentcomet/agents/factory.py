from typing import Any, List, Optional, Union
from .agent import Agent
from agentcomet.tools import ToolSpec
from agentcomet.models.base_model import BaseLLM

def create_agent(
    name: str,
    description: str = "",
    author: str = "",
    llm: Optional[Union[str, BaseLLM]] = None,
    tools: Optional[List[ToolSpec]] = None,
) -> Agent:
    """
    Declarative helper to create an Agent instance without subclassing.
    """
    class DynamicAgent(Agent):
        def setup(self):
            if tools:
                self.add_tools(*tools)
                
    return DynamicAgent(name=name, description=description, author=author, llm=llm)
