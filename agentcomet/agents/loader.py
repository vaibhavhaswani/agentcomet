from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass
from .base_agent import BaseAgent

try:
    from uaf_compiler.loader import UAFLoader
except ImportError:
    UAFLoader = None

try:
    from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
except ImportError:
    HumanMessage = None
    AIMessage = None
    BaseMessage = None


@dataclass
class AgentResponse:
    """
    Simplified response wrapper for agent outputs.
    Provides easy access to content while preserving full state.
    """
    content: str
    messages: List[Any]
    raw: Dict[str, Any]
    
    def __repr__(self):
        return f"AgentResponse(content='{self.content[:50]}...')" if len(self.content) > 50 else f"AgentResponse(content='{self.content}')"
    
    def __str__(self):
        return self.content


class UAFAgent(BaseAgent):
    """
    Wrapper for agents loaded from .uaf files.
    
    Provides a simplified interface that abstracts away LangGraph message formats.
    
    Args:
        name: Unique identifier for this agent
        uaf_path: Path to the .uaf file
        config: Optional configuration dict
        llm: LLM instance to inject into the agent
        memory: Memory mode - "full" to keep all messages, or an int to keep last N messages
    
    Example:
        agent = UAFAgent("math", "agent.uaf", llm=llm, memory="full")
        response = agent.invoke("What is 2+2?")
        print(response.content)  # "4"
    """
    
    def __init__(
        self, 
        name: str, 
        uaf_path: str, 
        config: Optional[Dict[str, Any]] = None, 
        llm: Any = None,
        memory: Union[str, int, None] = None
    ):
        super().__init__(name, config, llm=llm)
        self.uaf_path = uaf_path
        self.memory = memory
        self._message_history: List[Any] = []
        
        if UAFLoader is None:
            raise ImportError("uaf_compiler is required to load .uaf files.")
        
        self.loader = UAFLoader(uaf_path)
        self._load_runnable()
    
    def _load_runnable(self):
        """Load the runnable from the UAF file."""
        kwargs = {}
        if self.llm:
            kwargs['llm'] = self.llm
        
        try:
            result = self.loader.load(**kwargs)
        except TypeError:
            result = self.loader.load()
        
        if isinstance(result, tuple) and len(result) == 2:
            self.factory, self.meta = result
            if callable(self.factory):
                if self.llm and not kwargs:
                    try:
                        self.runnable = self.factory(llm=self.llm)
                    except TypeError:
                        self.runnable = self.factory()
                else:
                    self.runnable = self.factory()
            else:
                self.runnable = self.factory
        else:
            self.runnable = result
            self.meta = {}
    
    def _prepare_input(self, input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert plain text or dict input to LangGraph-compatible format.
        """
        if isinstance(input_data, str):
            # Plain text input - wrap in messages format
            if HumanMessage is None:
                raise ImportError("langchain_core is required for message handling. pip install langchain-core")
            
            new_message = HumanMessage(content=input_data)
            
            # Build messages with history
            messages = self._message_history.copy()
            messages.append(new_message)
            
            return {"messages": messages}
        
        elif isinstance(input_data, dict):
            # Already a dict - check if it has messages or wrap it
            if "messages" in input_data:
                # Prepend history to existing messages
                existing = input_data["messages"]
                if isinstance(existing, list):
                    input_data["messages"] = self._message_history + existing
                return input_data
            else:
                # No messages key - might be a different format, pass through
                return input_data
        else:
            raise ValueError(f"Input must be str or dict, got {type(input_data)}")
    
    def _extract_response(self, result: Any) -> AgentResponse:
        """
        Extract plain text content from LangGraph-style result.
        """
        content = ""
        messages = []
        raw = {}
        
        if isinstance(result, dict):
            raw = result
            messages = result.get("messages", [])
            
            # Find the last AI message
            if messages:
                for msg in reversed(messages):
                    if AIMessage and isinstance(msg, AIMessage):
                        content = msg.content
                        break
                    elif hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == 'ai':
                        content = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get('type') == 'ai':
                        content = msg.get('content', '')
                        break
                
                # Fallback: get last message content
                if not content and messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'content'):
                        content = last_msg.content
                    elif isinstance(last_msg, dict):
                        content = last_msg.get('content', str(last_msg))
                    else:
                        content = str(last_msg)
        else:
            raw = {"result": result}
            content = str(result)
        
        return AgentResponse(content=content, messages=messages, raw=raw)
    
    def _update_memory(self, messages: List[Any]):
        """Update message history based on memory setting."""
        if self.memory is None:
            # No memory - don't store anything
            return
        
        if self.memory == "full":
            # Store all messages
            self._message_history = list(messages)
        elif isinstance(self.memory, int) or (isinstance(self.memory, str) and self.memory.isdigit()):
            # Store last N messages
            n = int(self.memory)
            self._message_history = list(messages[-n:]) if len(messages) > n else list(messages)
    
    def invoke(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """
        Invoke the agent with simplified input/output.
        
        Args:
            input_data: Either a plain text string or a dict with state
            
        Returns:
            AgentResponse with .content (str), .messages (list), and .raw (dict)
        
        Example:
            response = agent.invoke("What is 2+2?")
            print(response.content)  # "4"
        """
        # Prepare input
        state = self._prepare_input(input_data)
        
        # Execute
        if hasattr(self.runnable, 'invoke'):
            result = self.runnable.invoke(state)
        elif callable(self.runnable):
            result = self.runnable(state)
        else:
            raise ValueError(f"Loaded agent {self.name} is neither a Runnable nor callable.")
        
        # Extract response
        response = self._extract_response(result)
        
        # Update memory
        self._update_memory(response.messages)
        
        return response
    
    def clear_memory(self):
        """Clear the message history."""
        self._message_history = []
    
    def get_history(self) -> List[Any]:
        """Get the current message history."""
        return self._message_history.copy()

    def reload(self):
        """
        Hot-reloads the agent from the .uaf file.
        Preserves memory/history.
        """
        print(f"Reloading agent {self.name} from {self.uaf_path}...")
        self.cleanup()
        
        self.loader = UAFLoader(self.uaf_path)
        self._load_runnable()

    def cleanup(self):
        """
        Clean up temporary directories extracted by UAFLoader.
        """
        if self.loader:
            self.loader.cleanup()

    def __del__(self):
        pass
