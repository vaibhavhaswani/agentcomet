from typing import Dict, List, Any, Optional
from .dag_builder import DAGBuilder
from .conditional_router import ConditionalRouter
from .patterns import Pattern

class WorkflowBuilder:
    """
    Declarative builder for multi-agent workflows.
    """
    def __init__(self, default_llm: Any = None):
        self.default_llm = default_llm
        self.agents: Dict[str, str] = {} # name -> uaf_path
        self.agent_configs: Dict[str, Dict[str, Any]] = {} # name -> {llm: ...}
        self.dag = DAGBuilder()
        self.routers: List[ConditionalRouter] = []
        self.parallel_groups: List[Dict[str, Any]] = []
        
    def add_agent(self, name: str, uaf_path: str, llm: Any = None):
        self.agents[name] = uaf_path
        self.agent_configs[name] = {"llm": llm}
        self.dag.add_node(name)
        
    def connect(self, start: str, end: str):
        self.dag.add_edge(start, end)
        
    def parallel(self, agents: List[str], merge_strategy: str = "consensus"):
        """
        Define a set of agents that run in parallel.
        """
        # Validate agents exist
        for agent in agents:
            if agent not in self.agents:
                raise ValueError(f"Agent {agent} not defined.")
        
        self.parallel_groups.append({
            "type": Pattern.PARALLEL,
            "agents": agents,
            "merge_strategy": merge_strategy
        })

    def route(self, from_agent: str, conditions: Dict[str, str]):
        """
        Define a conditional routing step.
        """
        if from_agent not in self.agents:
            raise ValueError(f"Agent {from_agent} not defined.")
        
        router = ConditionalRouter(from_agent, conditions)
        self.routers.append(router)
        
        # Implicitly add edges for the router destinations?
        # Or just store valid routing logic?
        # Let's add partial edges or mark them as conditional in the DAG?
        # For simplicity, we just store the router logic. The engine will handle the jump.
        for target in conditions.values():
            if target not in self.agents:
                raise ValueError(f"Target agent {target} in route condition not defined.")
            # We can purposefully NOT add a hard edge in DAG, or add a 'conditional' edge type.
