from typing import Any, Dict, Optional, Callable

class ConditionalRouter:
    """
    Handles conditional routing logic between agents.
    """
    def __init__(self, from_agent: str, conditions: Dict[str, str], condition_evaluator: Optional[Callable[[Any], str]] = None):
        """
        :param from_agent: The name of the agent where the route originates.
        :param conditions: A dictionary mapping condition results (keys) to target agent names (values).
        :param condition_evaluator: A callable that takes the agent output/state and returns a key to look up in 'conditions'.
                                    If None, assumes the output itself is the key.
        """
        self.from_agent = from_agent
        self.conditions = conditions
        self.condition_evaluator = condition_evaluator

    def get_next(self, output: Any) -> Optional[str]:
        """
        Determine the next agent based on the output.
        """
        key = output
        if self.condition_evaluator:
            key = self.condition_evaluator(output)
        
        # If output is a dict, maybe we look for a specific key? 
        # For now, stick to the simple contract: output -> condition key
        
        return self.conditions.get(str(key))
