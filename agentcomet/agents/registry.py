from typing import Dict, List
from .base_agent import BaseAgent

class AgentRegistry:
    """
    Registry to manage loaded agents.
    """
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """
        Register a new agent.
        """
        if agent.name in self._agents:
            # Overwrite or raise? For now, let's allow overwrite but maybe log warning
            # Actually, standard registry usually raises or returns false.
            # Let's simple allow overwrite for flexibility in reloading
            pass
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent:
        """
        Retrieve an agent by name.
        """
        if name not in self._agents:
            raise KeyError(f"Agent {name} not found in registry.")
        return self._agents[name]
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names.
        """
        return list(self._agents.keys())
