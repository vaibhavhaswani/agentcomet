from typing import Dict, Any, List, Deque
from ..agents import BaseAgent
from ..workflows import DAGBuilder, ConditionalRouter
from collections import deque

class ExecutionEngine:
    """
    Runtime execution engine for the workflows.
    """
    def __init__(self, agents: Dict[str, BaseAgent], dag: DAGBuilder, routers: List[ConditionalRouter]):
        self.agents = agents
        self.dag = dag
        self.routers = {r.from_agent: r for r in routers}
        
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the workflow given the initial input data.
        """
        state = input_data.copy()
        
        # Find start nodes (nodes with 0 in-degree in the static DAG)
        in_degree = {u: 0 for u in self.dag.nodes}
        for u, v in self.dag.edges:
            in_degree[v] += 1
            
        queue: Deque[str] = deque([u for u in self.dag.nodes if in_degree[u] == 0])
        processed = set()

        if not queue and self.dag.nodes:
            # If there are nodes but no clear start, pick the first added one?
            # Or maybe the user didn't connect anything.
            print("Warning: No start node detected (cycle or disconnected components).")
        
        while queue:
            node_name = queue.popleft()
            
            # Avoid infinite loops in this simple implementation
            # In real lifecycle, we might revisit nodes (loops).
            # For now, allow 1 visit per node per flow path usually, but let's just run.
            # To prevent strict infinite loops, maybe a max_steps?
            
            agent = self.agents.get(node_name)
            if not agent:
                print(f"Error: Agent {node_name} not found.")
                continue

            # Execute agent
            # We pass the full state.
            try:
                output = agent.invoke(state)
            except Exception as e:
                print(f"Error executing agent {node_name}: {e}")
                output = {}

            # Update state
            if isinstance(output, dict):
                state.update(output)
            
            # Helper to get routing key
            # We assume output might contain a special key 'route_key' or we check the whole output
            # For this simple engine, we check if output is a string (key) or a dict with 'decision' key
            route_key = output
            if isinstance(output, dict):
                route_key = output.get('decision') or output.get('route')

            # Determine next
            next_nodes = []
            
            # Check router
            if node_name in self.routers:
                router = self.routers[node_name]
                target = router.get_next(route_key)
                if target:
                    next_nodes.append(target)
            
            # If no router took over, follow standard DAG edges
            if not next_nodes:
                next_nodes = self.dag.adj_list.get(node_name, [])
            
            for next_node in next_nodes:
                queue.append(next_node)
                
        return state
