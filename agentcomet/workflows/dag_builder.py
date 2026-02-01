from typing import Dict, List, Set, Tuple, Any

class DAGBuilder:
    """
    Helper class to construct Direct Acyclic Graphs for workflows.
    """
    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[Tuple[str, str]] = []
        self.adj_list: Dict[str, List[str]] = {}
        
    def add_node(self, node: str):
        self.nodes.add(node)
        if node not in self.adj_list:
            self.adj_list[node] = []
        
    def add_edge(self, start: str, end: str):
        if start not in self.nodes:
            raise ValueError(f"Node {start} not found.")
        if end not in self.nodes:
            raise ValueError(f"Node {end} not found.")
        self.edges.append((start, end))
        self.adj_list[start].append(end)

    def validate(self):
        """
        Check for cycles and validity.
        """
        visited = set()
        recursion_stack = set()

        def dfs(node):
            visited.add(node)
            recursion_stack.add(node)
            for neighbor in self.adj_list.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
            recursion_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    raise ValueError("Cycle detected in workflow graph.")
