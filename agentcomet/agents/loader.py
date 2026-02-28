from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, asdict
from datetime import datetime
import os
import json
import hashlib
import shutil
import tempfile
import tarfile
import yaml
from .base_agent import BaseAgent

try:
    from uaf_compiler.loader import UAFLoader
except ImportError:
    UAFLoader = None

try:
    from uaf_compiler.compiler import UAFCompiler
except ImportError:
    UAFCompiler = None

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


@dataclass
class StateInfo:
    """Information about a saved state."""
    hash: str
    created_at: str
    message_count: int
    is_latest: bool = False
    
    def __repr__(self):
        latest = "[latest] " if self.is_latest else "         "
        return f"{latest}{self.hash}  {self.created_at}  ({self.message_count} messages)"

class AgentCometRuntime:
    """Runtime for Agents natively using the AgentComet SDK."""
    def __init__(self, uaf_path: str):
        self.uaf_path = uaf_path
        self.agent_dir = tempfile.mkdtemp(prefix="agentcomet_")
        
    def load(self, **kwargs) -> Any:
        # Extract files
        with tarfile.open(self.uaf_path, "r:gz") as tar:
            tar.extractall(path=self.agent_dir)
            
        import sys
        if self.agent_dir not in sys.path:
            sys.path.insert(0, self.agent_dir)
            
        # load agent.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("uaf_agent_module", os.path.join(self.agent_dir, "agent.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # entrypoint usually is agent or MyAgent
        return getattr(module, "agent", None)

class GenericUAFRuntime:
    """Fallback runtime for legacy or generic UAF agents."""
    def __init__(self, uaf_path: str):
        self.loader = UAFLoader(uaf_path) if UAFLoader else None
        
    def load(self, **kwargs) -> Any:
        if not self.loader:
            raise ImportError("uaf_compiler is required.")
        try:
            return self.loader.load(**kwargs)
        except TypeError:
            return self.loader.load()

def load_agent(uaf_path: str, **kwargs) -> Any:
    """
    Routs the loading sequence based on agent.yaml definition.
    Loads Agent SDK natively if sdk=agentcomet.
    """
    # 1. Parse agent.yaml from within tar
    sdk_name = None
    try:
        with tarfile.open(uaf_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "agent.yaml" or member.name.endswith("/agent.yaml"):
                    f = tar.extractfile(member)
                    manifest = yaml.safe_load(f)
                    sdk_name = manifest.get("sdk", {}).get("name", "")
                    break
    except Exception as e:
        print(f"Warning: could not parse agent.yaml: {e}")

    # 2. Route
    if sdk_name == "agentcomet":
        runtime = AgentCometRuntime(uaf_path)
    else:
        runtime = GenericUAFRuntime(uaf_path)
        
    return runtime.load(**kwargs)


try:
    from uaf_compiler.loader import UAFLoader
except ImportError:
    UAFLoader = None

try:
    from uaf_compiler.compiler import UAFCompiler
except ImportError:
    UAFCompiler = None

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


@dataclass
class StateInfo:
    """Information about a saved state."""
    hash: str
    created_at: str
    message_count: int
    is_latest: bool = False
    
    def __repr__(self):
        latest = "[latest] " if self.is_latest else "         "
        return f"{latest}{self.hash}  {self.created_at}  ({self.message_count} messages)"


class UAFAgent(BaseAgent):
    """
    Wrapper for agents loaded from .uaf files.
    
    Provides a simplified interface that abstracts away LangGraph message formats.
    Includes versioned state persistence for saving/loading conversation history.
    
    Args:
        name: Unique identifier for this agent
        uaf_path: Path to the .uaf file
        config: Optional configuration dict
        llm: LLM instance to inject into the agent
        memory: Memory mode - "full" to keep all messages, or an int to keep last N messages
        restore_state: If True, auto-load latest state on init
    
    Example:
        agent = UAFAgent("math", "agent.uaf", llm=llm, memory="full")
        response = agent.invoke("What is 2+2?")
        print(response.content)  # "4"
        
        # Save state
        state_hash = agent.save_state()
        
        # Show all states
        agent.show_states()
        
        # Export agent with state
        agent.save_agent("agent_v2.uaf")
    """
    
    STATE_DIR = ".agentcomet/states"
    STATE_VERSION = "1.0"
    
    def __init__(
        self, 
        name: str, 
        uaf_path: str, 
        config: Optional[Dict[str, Any]] = None, 
        llm: Any = None,
        memory: Union[str, int, None] = None,
        restore_state: bool = True
    ):
        super().__init__(name, config, llm=llm)
        self.uaf_path = os.path.abspath(uaf_path)
        self.memory = memory
        self._message_history: List[Any] = []
        
        if UAFLoader is None:
            raise ImportError("uaf_compiler is required to load .uaf files.")
        
        self.loader = UAFLoader(uaf_path)
        self._load_runnable()
        
        # Restore state if requested - try embedded state first, then external
        if restore_state:
            self._load_embedded_state()
    
    # =========================================================================
    # State Persistence Methods
    # =========================================================================
    
    def _load_embedded_state(self):
        """
        Load state embedded inside the .uaf file (agent.state).
        Falls back to external state storage if not found.
        Silently continues if no state exists.
        """
        # Check for embedded state in the extracted UAF
        try:
            # UAFLoader extracts to agent_dir, check for agent.state
            if hasattr(self.loader, 'agent_dir') and self.loader.agent_dir:
                embedded_state_path = os.path.join(self.loader.agent_dir, 'agent.state')
                if os.path.exists(embedded_state_path):
                    with open(embedded_state_path, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                    self._message_history = self._deserialize_messages(state_data.get("messages", []))
                    if self.memory is None:
                        saved_mode = state_data.get("memory_mode")
                        if saved_mode and saved_mode != "None":
                            self.memory = int(saved_mode) if saved_mode.isdigit() else saved_mode
                    print(f"Restored embedded state ({len(self._message_history)} messages)")
                    return
            
            # Fallback: try external state storage
            self.load_state()
        except Exception:
            # Silently continue if no state found
            pass
    
    def _get_state_dir(self) -> str:
        """Get the state directory for this agent."""
        base_dir = os.path.dirname(self.uaf_path)
        state_dir = os.path.join(base_dir, self.STATE_DIR, self.name)
        return state_dir
    
    def _get_index_path(self) -> str:
        """Get path to the state index file."""
        return os.path.join(self._get_state_dir(), "index.json")
    
    def _read_index(self) -> Dict:
        """Read the state index file."""
        index_path = self._get_index_path()
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"agent_name": self.name, "states": [], "latest": None}
    
    def _write_index(self, index: Dict):
        """Write the state index file."""
        state_dir = self._get_state_dir()
        os.makedirs(state_dir, exist_ok=True)
        index_path = self._get_index_path()
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)
    
    def _serialize_messages(self) -> List[Dict]:
        """Serialize message history to JSON-compatible format."""
        serialized = []
        for msg in self._message_history:
            if hasattr(msg, 'type') and hasattr(msg, 'content'):
                # LangChain message object
                serialized.append({
                    "type": msg.type,
                    "content": msg.content
                })
            elif isinstance(msg, dict):
                serialized.append(msg)
            else:
                serialized.append({"type": "unknown", "content": str(msg)})
        return serialized
    
    def _deserialize_messages(self, data: List[Dict]) -> List[Any]:
        """Deserialize messages from JSON format."""
        messages = []
        for item in data:
            msg_type = item.get("type", "unknown")
            content = item.get("content", "")
            
            if msg_type == "human" and HumanMessage:
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai" and AIMessage:
                messages.append(AIMessage(content=content))
            else:
                # Fallback: keep as dict
                messages.append(item)
        return messages
    
    def _hash_state(self, state_data: Dict) -> str:
        """Generate SHA-256 hash for state data."""
        # Create deterministic string representation
        content = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:8]
    
    def save_state(self) -> str:
        """
        Save current state with version control.
        
        Returns:
            str: Hash of the saved state
            
        Example:
            hash = agent.save_state()
            print(f"Saved state: {hash}")
        """
        # Build state data
        now = datetime.now()
        state_data = {
            "version": self.STATE_VERSION,
            "agent_name": self.name,
            "uaf_path": self.uaf_path,
            "created_at": now.isoformat(),
            "memory_mode": str(self.memory),
            "message_count": len(self._message_history),
            "messages": self._serialize_messages(),
            "metadata": {}
        }
        
        # Generate hash
        state_hash = self._hash_state(state_data)
        state_data["hash"] = state_hash
        
        # Ensure directory exists
        state_dir = self._get_state_dir()
        os.makedirs(state_dir, exist_ok=True)
        
        # Write state file
        state_path = os.path.join(state_dir, f"{state_hash}.state")
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
        
        # Update index
        index = self._read_index()
        
        # Check if this hash already exists
        existing_hashes = [s["hash"] for s in index["states"]]
        if state_hash not in existing_hashes:
            index["states"].append({
                "hash": state_hash,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "message_count": len(self._message_history)
            })
        
        index["latest"] = state_hash
        self._write_index(index)
        
        print(f"[{state_hash}] State saved ({len(self._message_history)} messages)")
        return state_hash
    
    def load_state(self, state_hash: str = None) -> bool:
        """
        Load state from a saved version.
        
        Args:
            state_hash: Hash of state to load, or None for latest
            
        Returns:
            bool: True if state was loaded, False otherwise
            
        Example:
            agent.load_state("a1b2c3d4")  # Load specific state
            agent.load_state()            # Load latest state
        """
        index = self._read_index()
        
        # Get hash to load
        if state_hash is None:
            state_hash = index.get("latest")
            if not state_hash:
                print("No saved states found.")
                return False
        
        # Load state file
        state_path = os.path.join(self._get_state_dir(), f"{state_hash}.state")
        if not os.path.exists(state_path):
            print(f"State {state_hash} not found.")
            return False
        
        with open(state_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        # Restore messages
        self._message_history = self._deserialize_messages(state_data.get("messages", []))
        
        # Restore memory mode if not set
        if self.memory is None:
            saved_mode = state_data.get("memory_mode")
            if saved_mode and saved_mode != "None":
                self.memory = int(saved_mode) if saved_mode.isdigit() else saved_mode
        
        print(f"Loaded state {state_hash} ({len(self._message_history)} messages)")
        return True
    
    def show_states(self) -> List[StateInfo]:
        """
        Display all saved states for this agent.
        
        Returns:
            List[StateInfo]: List of state information objects
            
        Example:
            states = agent.show_states()
            # Output:
            # States for 'math_agent':
            #   [latest] e5f6g7h8  2026-02-01 23:35  (6 messages)
            #            a1b2c3d4  2026-02-01 23:30  (2 messages)
        """
        index = self._read_index()
        states = index.get("states", [])
        latest = index.get("latest")
        
        if not states:
            print(f"No saved states for '{self.name}'")
            return []
        
        print(f"\nStates for '{self.name}':")
        
        result = []
        # Show in reverse order (newest first)
        for s in reversed(states):
            info = StateInfo(
                hash=s["hash"],
                created_at=s["created_at"],
                message_count=s["message_count"],
                is_latest=(s["hash"] == latest)
            )
            result.append(info)
            print(f"  {info}")
        
        print()
        return result
    
    def save_agent(self, path: str, state: str = None) -> str:
        """
        Export agent as a new .uaf file with state embedded inside.
        
        Uses UAFLoader.update() and apply_updates() to embed the state
        as 'agent.state' inside the .uaf archive.
        
        Args:
            path: Output path for the new .uaf file
            state: Hash of state to embed, or None for current memory
            
        Returns:
            str: Path to the created .uaf file
            
        Example:
            agent.save_agent("agent_v2.uaf")  # With current memory state
            agent.save_agent("agent_v2.uaf", state="a1b2c3d4")  # With specific saved state
        """
        output_path = os.path.abspath(path)
        
        # Get state data to embed
        state_data = None
        
        if state:
            # Load from saved state hash
            state_file = os.path.join(self._get_state_dir(), f"{state}.state")
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
        else:
            # Use current memory state
            if self._message_history:
                now = datetime.now()
                state_data = {
                    "version": self.STATE_VERSION,
                    "agent_name": self.name,
                    "uaf_path": self.uaf_path,
                    "created_at": now.isoformat(),
                    "memory_mode": str(self.memory),
                    "message_count": len(self._message_history),
                    "messages": self._serialize_messages(),
                    "metadata": {}
                }
        
        # Copy original UAF to new path
        shutil.copy2(self.uaf_path, output_path)
        
        # Embed state inside the UAF using UAFLoader.update()
        if state_data:
            # Create temp file for state JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
                temp_state_path = f.name
            
            try:
                # Create new UAFLoader for the output file
                output_loader = UAFLoader(output_path)
                
                # Queue the state file update (type="state" -> agent.state)
                output_loader.update(temp_state_path, type="state")
                
                # Apply the updates to embed state in the UAF
                output_loader.apply_updates()
                
                print(f"Saved agent to {output_path} with embedded state ({state_data.get('message_count', 0)} messages)")
            finally:
                # Clean up temp file
                if os.path.exists(temp_state_path):
                    os.unlink(temp_state_path)
        else:
            print(f"Saved agent to {output_path} (no state)")
        
        return output_path
    
    def delete_state(self, state_hash: str) -> bool:
        """
        Delete a specific state version.
        
        Args:
            state_hash: Hash of state to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        index = self._read_index()
        
        # Find and remove from index
        states = index.get("states", [])
        new_states = [s for s in states if s["hash"] != state_hash]
        
        if len(new_states) == len(states):
            print(f"State {state_hash} not found.")
            return False
        
        # Delete state file
        state_path = os.path.join(self._get_state_dir(), f"{state_hash}.state")
        if os.path.exists(state_path):
            os.remove(state_path)
        
        # Update index
        index["states"] = new_states
        if index.get("latest") == state_hash:
            index["latest"] = new_states[-1]["hash"] if new_states else None
        self._write_index(index)
        
        print(f"Deleted state {state_hash}")
        return True
    
    # =========================================================================
    # Core Agent Methods
    # =========================================================================
    
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
        """Convert plain text or dict input to LangGraph-compatible format."""
        if isinstance(input_data, str):
            if HumanMessage is None:
                raise ImportError("langchain_core is required for message handling.")
            
            new_message = HumanMessage(content=input_data)
            messages = self._message_history.copy()
            messages.append(new_message)
            return {"messages": messages}
        
        elif isinstance(input_data, dict):
            if "messages" in input_data:
                existing = input_data["messages"]
                if isinstance(existing, list):
                    input_data["messages"] = self._message_history + existing
                return input_data
            else:
                return input_data
        else:
            raise ValueError(f"Input must be str or dict, got {type(input_data)}")
    
    def _extract_response(self, result: Any) -> AgentResponse:
        """Extract plain text content from LangGraph-style result."""
        content = ""
        messages = []
        raw = {}
        
        if isinstance(result, dict):
            raw = result
            messages = result.get("messages", [])
            
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
            return
        
        if self.memory == "full":
            self._message_history = list(messages)
        elif isinstance(self.memory, int) or (isinstance(self.memory, str) and self.memory.isdigit()):
            n = int(self.memory)
            self._message_history = list(messages[-n:]) if len(messages) > n else list(messages)
    
    def invoke(self, input_data: Union[str, Dict[str, Any]]) -> AgentResponse:
        """
        Invoke the agent with simplified input/output.
        
        Args:
            input_data: Either a plain text string or a dict with state
            
        Returns:
            AgentResponse with .content (str), .messages (list), and .raw (dict)
        """
        state = self._prepare_input(input_data)
        
        if hasattr(self.runnable, 'invoke'):
            result = self.runnable.invoke(state)
        elif callable(self.runnable):
            result = self.runnable(state)
        else:
            raise ValueError(f"Loaded agent {self.name} is neither a Runnable nor callable.")
        
        response = self._extract_response(result)
        self._update_memory(response.messages)
        return response
    
    def clear_memory(self):
        """Clear the message history."""
        self._message_history = []
    
    def get_history(self) -> List[Any]:
        """Get the current message history."""
        return self._message_history.copy()

    def reload(self):
        """Hot-reloads the agent from the .uaf file. Preserves memory/history."""
        print(f"Reloading agent {self.name} from {self.uaf_path}...")
        self.cleanup()
        self.loader = UAFLoader(self.uaf_path)
        self._load_runnable()

    def cleanup(self):
        """Clean up temporary directories extracted by UAFLoader."""
        if self.loader:
            self.loader.cleanup()

    def __del__(self):
        pass
