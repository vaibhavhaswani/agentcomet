from typing import Dict, Any, Optional
from ..agents import BaseAgent
from ..agents.loader import load_agent
from ..workflows import WorkflowBuilder
from .execution_engine import ExecutionEngine
from ..communication import MessageBroker

class AgentOrchestrator:
    """
    Main orchestration class for executing workflows.
    """
    def __init__(self, workflow: Optional[WorkflowBuilder] = None, llm: Any = None):
        self.workflow = workflow or WorkflowBuilder()
        if llm:
            # Override workflow default if provided top-level
            self.workflow.default_llm = llm
            
        self.message_broker = None
        self._execution_engine = None
        self._loaded_agents: Dict[str, BaseAgent] = {}

    def add_agent(self, name: str, uaf_path: str, llm: Any = None):
        self.workflow.add_agent(name, uaf_path, llm=llm)

    def connect(self, start: str, end: str):
        self.workflow.connect(start, end)

    def set_message_broker(self, broker: MessageBroker):
        self.message_broker = broker

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alias for execute.
        """
        return self.execute(input_data)

    def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the workflow.
        """
        # Load agents defined in the workflow
        for name, path in self.workflow.agents.items():
            if name not in self._loaded_agents:
                try:
                    # Resolve LLM: Agent Specific > Workflow Default
                    agent_config = self.workflow.agent_configs.get(name, {})
                    effective_llm = agent_config.get("llm") or self.workflow.default_llm
                    
                    agent = load_agent(path)
                    
                    # If the agent supports receiving the broker, inject it
                    # (This assumes the underlying runnable or agent object has a way to accept it)
                    if hasattr(agent.runnable, 'set_message_broker') and self.message_broker:
                        agent.runnable.set_message_broker(self.message_broker)
                    
                    self._loaded_agents[name] = agent
                except Exception as e:
                    print(f"Error loading agent {name} from {path}: {e}")
                    # For system stability, might raise or skip. 
                    # Raising is safer.
                    raise e

        # Initialize engine
        self._execution_engine = ExecutionEngine(
            agents=self._loaded_agents, 
            dag=self.workflow.dag, 
            routers=self.workflow.routers
        )
        
        return self._execution_engine.run(initial_state)
