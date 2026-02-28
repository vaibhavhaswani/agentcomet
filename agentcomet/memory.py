import json
import os
from typing import Any, Optional


class Memory:
    """
    Simple key-value memory store for AgentComet agents.
    
    Usage:
        self.memory.save("username", "Alice")
        self.memory.get("username")  # -> "Alice"
    
    Under the hood:
        - Backed by a Python dict
        - Auto-serialized to JSON (agent.state)
        - Auto-packed into .uaf during export
        - Auto-restored during load_agent()
        - User never touches .state files directly
    """
    
    def __init__(self):
        self._store: dict = {}
    
    def save(self, key: str, value: Any):
        """Save a value to memory."""
        self._store[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory."""
        return self._store.get(key, default)
    
    def delete(self, key: str):
        """Remove a key from memory."""
        self._store.pop(key, None)
    
    def has(self, key: str) -> bool:
        """Check if a key exists in memory."""
        return key in self._store
    
    def keys(self) -> list:
        """List all keys in memory."""
        return list(self._store.keys())
    
    def clear(self):
        """Clear all memory."""
        self._store.clear()
    
    def to_dict(self) -> dict:
        """Serialize memory to a dict."""
        return dict(self._store)
    
    def from_dict(self, data: dict):
        """Restore memory from a dict."""
        self._store = dict(data)
    
    def to_json(self) -> str:
        """Serialize memory to JSON string."""
        return json.dumps(self._store, default=str)
    
    def from_json(self, data: str):
        """Restore memory from JSON string."""
        self._store = json.loads(data)

    def __repr__(self):
        return f"Memory({len(self._store)} keys: {self.keys()})"
