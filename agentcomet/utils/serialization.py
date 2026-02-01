import json
import pickle
from typing import Any

class StateSerializer:
    """
    Helper for serializing workflow state.
    """
    @staticmethod
    def to_json(data: Any) -> str:
        # Default to string for non-serializable objects?
        return json.dumps(data, default=str)
    
    @staticmethod
    def from_json(data: str) -> Any:
        return json.loads(data)
    
    @staticmethod
    def to_bytes(data: Any) -> bytes:
        return pickle.dumps(data)
    
    @staticmethod
    def from_bytes(data: bytes) -> Any:
        return pickle.loads(data)
