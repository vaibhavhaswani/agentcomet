from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Union

class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.
    """
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        messages format: [{'role': 'user', 'content': '...'}, ...]
        """
        pass
