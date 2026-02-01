from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the AgentComet framework.
    """
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None, llm: Any = None):
        self.name = name
        self.config = config or {}
        self.llm = llm

    @abstractmethod
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent logic given the current state.
        Returns the updated state or a dictionary of updates.
        """
        pass
