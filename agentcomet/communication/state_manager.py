from typing import Any, Dict

class StateManager:
    """
    Manages shared state for the workflow.
    """
    def __init__(self, initial_state: Dict[str, Any] = None):
        self._state = initial_state or {}

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def set(self, key: str, value: Any):
        self._state[key] = value

    def update(self, updates: Dict[str, Any]):
        self._state.update(updates)
        
    def get_all(self) -> Dict[str, Any]:
        return self._state.copy()
