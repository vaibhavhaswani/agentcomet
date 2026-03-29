from typing import Any, Dict, Optional
import os
import json
import tempfile
import tarfile
import yaml

try:
    from uaf_cli.loader import UAFLoader
except ImportError:
    UAFLoader = None



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
        agent = getattr(module, "agent", None)
        
        # Auto-restore memory from agent.state if it exists
        state_path = os.path.join(self.agent_dir, "agent.state")
        if agent and os.path.exists(state_path):
            try:
                import json
                with open(state_path, "r") as f:
                    state_data = json.load(f)
                if hasattr(agent, 'memory'):
                    agent.memory.from_dict(state_data)
            except Exception:
                pass  # Silently skip if state is malformed
        
        return agent

class GenericUAFRuntime:
    """Fallback runtime for legacy or generic UAF agents."""
    def __init__(self, uaf_path: str):
        self.loader = UAFLoader(uaf_path) if UAFLoader else None
        
    def load(self, **kwargs) -> Any:
        if not self.loader:
            raise ImportError("uaf-cli is required.")
        try:
            return self.loader.load(**kwargs)
        except TypeError:
            return self.loader.load()

def load_agent(uaf_path: str, **kwargs) -> Any:
    """
    Routes the loading sequence based on agent.yaml definition.
    Loads Agent SDK natively if type=agentcomet or sdk.name=agentcomet.
    """
    # 1. Parse agent.yaml from within tar
    agent_type = None
    try:
        with tarfile.open(uaf_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "agent.yaml" or member.name.endswith("/agent.yaml"):
                    f = tar.extractfile(member)
                    manifest = yaml.safe_load(f)
                    # v1 schema: type field
                    agent_type = manifest.get("type", "")
                    # v2 fallback: sdk.name
                    if not agent_type:
                        agent_type = manifest.get("sdk", {}).get("name", "")
                    break
    except Exception as e:
        print(f"Warning: could not parse agent.yaml: {e}")

    # 2. Route
    if agent_type == "agentcomet":
        runtime = AgentCometRuntime(uaf_path)
    else:
        runtime = GenericUAFRuntime(uaf_path)
        
    return runtime.load(**kwargs)


