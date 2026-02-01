from typing import List, Dict, Any
from .workflow_builder import WorkflowBuilder

class WorkflowTemplates:
    """
    Factory for common workflow patterns.
    """
    
    @staticmethod
    def pipeline(agents_map: Dict[str, str]) -> WorkflowBuilder:
        """
        Creates a linear pipeline A -> B -> C ...
        agents_map: OrderedDict or just dict of {name: uaf_path} in sequence.
        Note: Python dicts are ordered since 3.7.
        """
        builder = WorkflowBuilder()
        names = list(agents_map.keys())
        
        # Add all agents
        for name, path in agents_map.items():
            builder.add_agent(name, path)
            
        # Connect sequentially
        for i in range(len(names) - 1):
            builder.connect(names[i], names[i+1])
            
        return builder

    @staticmethod
    def fan_out_fan_in(
        start_agent: Dict[str, str], # {name: path}
        parallel_agents: Dict[str, str], # {name: path}
        end_agent: Dict[str, str] # {name: path}
    ) -> WorkflowBuilder:
        """
        Start -> [P1, P2, P3] -> End
        """
        builder = WorkflowBuilder()
        
        # Start
        s_name, s_path = list(start_agent.items())[0]
        builder.add_agent(s_name, s_path)
        
        # End
        e_name, e_path = list(end_agent.items())[0]
        builder.add_agent(e_name, e_path)
        
        # Parallel
        p_names = []
        for name, path in parallel_agents.items():
            builder.add_agent(name, path)
            p_names.append(name)
            
        # Connect
        for p in p_names:
            builder.connect(s_name, p)
            # We don't have a direct "join" node in DAGBuilder that waits for all?
            # Our ExecutionEngine logic for parallel isn't fully robust yet.
            # But normally DAG supports this: End depends on P1, P2, P3.
            # So End won't start until P1, P2, P3 are done (if Engine supports join).
            # My simple engine checks if in_degree is satisfied?
            # Let's check ExecutionEngine.
            builder.connect(p, e_name)
            
        return builder

    @staticmethod
    def map_reduce(
        mapper: Dict[str, str], # {name: path}
        workers: Dict[str, str], # {name_prefix: path} - will instantiate multiple? or just assume parallel agents
        reducer: Dict[str, str] # {name: path}
    ) -> WorkflowBuilder:
        # Simplified: just fan-out fan-in
        return WorkflowTemplates.fan_out_fan_in(mapper, workers, reducer)
