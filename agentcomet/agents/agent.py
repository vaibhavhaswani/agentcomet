import os
import tempfile
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from agentcomet.agents.base_agent import BaseAgent
from agentcomet.models.base_model import BaseLLM
from agentcomet.memory import Memory
from agentcomet.tools import ToolSpec, ToolRegistry, default_registry


class Agent(BaseAgent):
    """
    Agent class for AgentComet SDK.
    
    Features:
        - Declarative setup via setup() override
        - Tool calling with @tool decorator
        - Key-value memory (self.memory.save / self.memory.get)
        - State persistence (save_state / load_state / show_states)
        - UAF export/load (agent.export / load_agent)
    """
    
    STATE_DIR = ".agentcomet"
    
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None, 
                 author: Optional[str] = None, llm: Optional[Union[str, BaseLLM]] = None):
        self.description = description or "This is a tool calling agent that solves tasks using its assigned tools."
        self.author = author or "AgentComet"
        self._llm_provider = None
        self._llm_instance = None
        self.memory = Memory()
        self.registry = ToolRegistry()
        self._states_index = {}  # name -> hash mapping
        
        # Pull in default builtins
        for tool_name, tool_spec in default_registry.builtin_tools.items():
            self.registry.register_builtin(tool_spec)
            
        self.setup()

        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if author is not None:
            self.author = author
        if llm is not None:
            self.use_llm(llm)

        if not hasattr(self, 'name') or not self.name:
            self.name = "default-agent"

        super().__init__(name=self.name)
        
    def setup(self):
        """Intended to be overridden by subclasses to configure the agent."""
        pass
        
    # ── LLM ─────────────────────────────────────────────────────────────
        
    def use_llm(self, model: Union[str, BaseLLM]):
        """Configure the LLM provider. Accepts a BaseLLM instance or a string like 'ollama:gemma3:4b'."""
        if isinstance(model, BaseLLM):
            self._llm_instance = model
            cls_name = type(model).__name__.lower()
            model_name = getattr(model, 'model', 'unknown')
            self._llm_provider = f"{cls_name}:{model_name}"
        elif isinstance(model, str):
            self._llm_provider = model
            provider, _, model_name = model.partition(":")
            if provider == "ollama":
                from agentcomet.models.providers import Ollama
                self._llm_instance = Ollama(model=model_name or "llama3")
        
    def use_memory(self, enabled: bool = True):
        """Legacy compatibility — memory is always available via self.memory."""
        pass
        
    # ── Tools ───────────────────────────────────────────────────────────
        
    def add_tools(self, *tools: ToolSpec):
        """Add tools to the agent's registry."""
        for tool in tools:
            self.registry.register_agent_tool(tool)
            
    # ── Invoke / Chat / Run ─────────────────────────────────────────────
            
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Base implementation from BaseAgent. Wraps chat."""
        user_input = state.get("input", "")
        if not user_input and "messages" in state:
            messages = state["messages"]
            if messages:
                user_input = messages[-1].content
        
        response = self.chat(user_input)
        return {"output": response}

    def _build_tool_descriptions(self) -> str:
        """Build detailed tool descriptions for the LLM prompt."""
        tools = self.registry.get_all_tools()
        if not tools:
            return ""
        
        desc = "You have access to the following tools. To use a tool, respond with EXACTLY this format on its own line:\n"
        desc += "TOOL_CALL: tool_name(arg1=value1, arg2=value2)\n\n"
        desc += "Available tools:\n"
        for t in tools:
            params = ""
            if t.schema and "properties" in t.schema:
                props = t.schema["properties"]
                param_parts = []
                for pname, pinfo in props.items():
                    ptype = pinfo.get("type", "any")
                    pdesc = pinfo.get("description", "")
                    param_parts.append(f"{pname}: {ptype}" + (f" - {pdesc}" if pdesc else ""))
                params = ", ".join(param_parts)
            desc += f"  - {t.name}({params}): {t.description}\n"
            
        desc += "\nCRITICAL INSTRUCTIONS:\n"
        desc += "1. ONLY use tools if the user EXPLICITLY asks you to perform an action that requires them.\n"
        desc += "2. DO NOT use tools (like write/read files) just to remember user information. I automatically save our conversation history.\n"
        desc += "3. If you do not need a tool, just respond directly.\n"
        desc += "4. After receiving a tool result, provide your final answer to the user.\n"
        return desc
    
    def _parse_tool_call(self, response: str):
        """Parse a TOOL_CALL from the LLM response. Returns (tool_name, kwargs) or None."""
        import re
        # Match: TOOL_CALL: func_name(arg=val, ...)
        pattern = r'TOOL_CALL:\s*(\w+)\(([^)]*)\)'
        match = re.search(pattern, response)
        if not match:
            # Also try: ```tool_code\nfunc(args)\n```
            pattern2 = r'```tool_code\s*\n\s*(\w+)\(([^)]*)\)\s*\n```'
            match = re.search(pattern2, response)
        if not match:
            return None
        
        func_name = match.group(1)
        args_str = match.group(2).strip()
        
        kwargs = {}
        if args_str:
            for part in re.split(r',\s*(?=\w+=)', args_str):
                part = part.strip()
                if '=' in part:
                    key, val = part.split('=', 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    # Try to convert to int/float
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                    kwargs[key] = val
        
        return func_name, kwargs
    
    def _execute_tool(self, tool_name: str, kwargs: dict) -> str:
        """Execute a tool by name with given kwargs."""
        tools = {t.name: t for t in self.registry.get_all_tools()}
        if tool_name not in tools:
            return f"Error: Tool '{tool_name}' not found."
        
        tool_spec = tools[tool_name]
        try:
            result = tool_spec.fn(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def chat(self, input: str) -> str:
        """Core method to invoke the model with memory context and tool calling."""
        # Build memory context for the prompt
        memory_context = ""
        mem = self.memory.to_dict()
        
        # Include stored facts (non-messages keys)
        facts = {k: v for k, v in mem.items() if k != "messages"}
        if facts:
            memory_context += "Known Information:\n"
            for k, v in facts.items():
                memory_context += f"  {k}: {v}\n"
        
        # Include conversation history
        messages = mem.get("messages", [])
        if messages:
            memory_context += "\nConversation History:\n"
            for msg in messages[-10:]:
                role = msg.get("role", "unknown")
                text = msg.get("text", "")
                memory_context += f"  [{role}] {text}\n"
        
        if self._llm_instance:
            try:
                # Build prompt with tool descriptions
                prompt_parts = []
                if memory_context:
                    prompt_parts.append(memory_context)
                
                tool_desc = self._build_tool_descriptions()
                if tool_desc:
                    prompt_parts.append(tool_desc)
                
                prompt_parts.append(f"User: {input}")
                prompt = "\n".join(prompt_parts)
                
                # Tool-calling loop (up to 3 rounds)
                final_response = ""
                for _ in range(3):
                    response = self._llm_instance.generate(prompt)
                    
                    tool_call = self._parse_tool_call(response)
                    if tool_call:
                        tool_name, kwargs = tool_call
                        result = self._execute_tool(tool_name, kwargs)
                        # Feed result back to LLM
                        prompt += f"\n\nAssistant: {response}\n\nTool Result for {tool_name}: {result}\n\nNow provide your final answer to the user based on the tool result."
                    else:
                        final_response = response
                        break
                else:
                    final_response = response
                
                # Auto-append to conversation history
                if "messages" not in mem:
                    mem["messages"] = []
                mem["messages"].append({"role": "user", "text": input})
                mem["messages"].append({"role": "agent", "text": final_response})
                self.memory.save("messages", mem["messages"])
                
                return final_response
            except Exception as e:
                return f"[Agent: {self.name}] Error invoking LLM {self._llm_provider}: {e}"
                
        return f"[Agent: {self.name}] No LLM configured. Input: {input}"

    def run(self, input: str) -> str:
        """Run the agent."""
        return self.chat(input)

    # ── State Persistence ───────────────────────────────────────────────
    
    def _get_state_dir(self) -> str:
        """Get the state directory for this agent."""
        state_dir = os.path.join(self.STATE_DIR, "states", self.name)
        os.makedirs(state_dir, exist_ok=True)
        return state_dir
    
    def _get_index_path(self) -> str:
        return os.path.join(self._get_state_dir(), "index.json")
    
    def _read_index(self) -> dict:
        path = self._get_index_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"states": [], "latest": None, "names": {}}
    
    def _write_index(self, index: dict):
        with open(self._get_index_path(), 'w') as f:
            json.dump(index, f, indent=2)
    
    def _generate_hash(self, data: dict) -> str:
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:8]
    
    def save_state(self, name: Optional[str] = None) -> str:
        """
        Save current memory state. Returns hash or name.
        
        Args:
            name: Optional friendly name (e.g. "checkpoint1"). 
                  If not provided, an auto-generated hash is returned.
        
        Examples:
            hash = agent.save_state()               # -> "a1b2c3d4"
            agent.save_state("before-training")      # -> "before-training"
        """
        now = datetime.now()
        state_data = {
            "agent_name": self.name,
            "created_at": now.isoformat(),
            "memory": self.memory.to_dict()
        }
        
        state_hash = self._generate_hash(state_data)
        state_data["hash"] = state_hash
        
        state_dir = self._get_state_dir()
        
        # Write the state file (always keyed by hash)
        state_path = os.path.join(state_dir, f"{state_hash}.state")
        with open(state_path, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        # Update index
        index = self._read_index()
        existing = [s["hash"] for s in index["states"]]
        if state_hash not in existing:
            index["states"].append({
                "hash": state_hash,
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "key_count": len(self.memory.to_dict())
            })
        
        index["latest"] = state_hash
        
        # Register name -> hash mapping
        if "names" not in index:
            index["names"] = {}
        if name:
            index["names"][name] = state_hash
            
        self._write_index(index)
        
        label = name or state_hash
        print(f"[{label}] State saved ({len(self.memory.to_dict())} keys)")
        return label
    
    def load_state(self, identifier: Optional[str] = None) -> bool:
        """
        Load a saved state by hash, name, or latest.
        
        Args:
            identifier: Hash, friendly name, or None for latest.
        
        Examples:
            agent.load_state("a1b2c3d4")         # by hash
            agent.load_state("before-training")    # by name
            agent.load_state()                     # latest
        """
        index = self._read_index()
        
        if identifier is None:
            state_hash = index.get("latest")
            if not state_hash:
                print("No saved states found.")
                return False
        else:
            # Check if it's a name first
            names = index.get("names", {})
            state_hash = names.get(identifier, identifier)
        
        state_path = os.path.join(self._get_state_dir(), f"{state_hash}.state")
        if not os.path.exists(state_path):
            print(f"State '{identifier or state_hash}' not found.")
            return False
        
        with open(state_path, 'r') as f:
            state_data = json.load(f)
        
        self.memory.from_dict(state_data.get("memory", {}))
        print(f"Loaded state '{identifier or state_hash}' ({len(self.memory.to_dict())} keys)")
        return True
    
    def show_states(self) -> list:
        """Show all saved states for this agent."""
        index = self._read_index()
        states = index.get("states", [])
        latest = index.get("latest")
        names = index.get("names", {})
        
        # Reverse name map: hash -> name
        hash_to_name = {v: k for k, v in names.items()}
        
        if not states:
            print(f"No saved states for '{self.name}'")
            return []
        
        print(f"\nStates for '{self.name}':")
        result = []
        for s in reversed(states):
            is_latest = s["hash"] == latest
            tag = "[latest] " if is_latest else "         "
            friendly = f" ({hash_to_name[s['hash']]})" if s["hash"] in hash_to_name else ""
            print(f"  {tag}{s['hash']}{friendly}  {s['created_at']}  ({s['key_count']} keys)")
            result.append(s)
        print()
        return result
    
    def delete_state(self, identifier: str):
        """Delete a saved state by hash or name."""
        index = self._read_index()
        names = index.get("names", {})
        state_hash = names.get(identifier, identifier)
        
        state_path = os.path.join(self._get_state_dir(), f"{state_hash}.state")
        if os.path.exists(state_path):
            os.remove(state_path)
        
        index["states"] = [s for s in index["states"] if s["hash"] != state_hash]
        
        # Remove name mapping if exists
        names_to_remove = [k for k, v in names.items() if v == state_hash]
        for k in names_to_remove:
            del names[k]
        
        if index.get("latest") == state_hash:
            index["latest"] = index["states"][-1]["hash"] if index["states"] else None
            
        self._write_index(index)
        print(f"Deleted state '{identifier}'")

    # ── UAF Export ──────────────────────────────────────────────────────

    def export(self, path: str, version: str = "0.1.0"):
        """
        Export the Agent into a UAF format using the v2 Manifest structure.
        Memory is auto-serialized into agent.state inside the archive.
        """
        import tempfile
        import shutil
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            all_t = self.registry.get_all_tools()
            builtin_names = [t.name for t in all_t if t.name in default_registry.builtin_tools]
            custom_names = [t.name for t in all_t if t.name not in default_registry.builtin_tools]

            has_state = len(self.memory.to_dict()) > 0

            # --- 1. agent.yaml (v2 schema — matches UAFv2AgentYaml) ---
            manifest = {
                "uaf_version": 2,
                "agent": {
                    "name": self.name,
                    "version": version,
                    "description": self.description,
                    "author": self.author
                },
                "runtime": {
                    "engine": "python",
                    "entrypoint": "agent.py"
                },
                "sdk": {
                    "name": "agentcomet",
                    "version": "0.1.0"
                },
                "tools": {
                    "builtin": builtin_names,
                    "custom": custom_names
                },
                "state": {
                    "enabled": has_state,
                    "file": "agent.state" if has_state else None
                },
                "dependencies": {
                    "auto": True
                }
            }
                
            with open(os.path.join(temp_dir, 'agent.yaml'), 'w') as f:
                import yaml
                yaml.dump(manifest, f, sort_keys=False)
                
            # --- 2. agent.py ---
            with open(os.path.join(temp_dir, 'agent.py'), 'w') as f:
                f.write("from agentcomet.agents.factory import create_agent\n")
                if builtin_names:
                    f.write("from agentcomet.tools import " + ", ".join(builtin_names) + "\n")
                if custom_names:
                    f.write("from tools import " + ", ".join(custom_names) + "\n")
                f.write("\n")
                
                tool_list_str = "[" + ", ".join(builtin_names + custom_names) + "]"
                
                f.write(f"agent = create_agent(\n")
                f.write(f"    name='{self.name}',\n")
                f.write(f"    description='{self.description}',\n")
                f.write(f"    author='{self.author}',\n")
                f.write(f"    llm='{self._llm_provider}',\n")
                if builtin_names or custom_names:
                    f.write(f"    tools={tool_list_str},\n")
                f.write(")\n")
                
            # --- 3. tools.py ---
            if custom_names:
                with open(os.path.join(temp_dir, 'tools.py'), 'w') as f:
                    f.write("from agentcomet.tools import tool\n\n")
                    import inspect
                    for t_name in custom_names:
                        t_spec = [t for t in all_t if t.name == t_name][0]
                        try:
                            source = inspect.getsource(t_spec.fn)
                            f.write(source + "\n\n")
                        except Exception as e:
                            f.write(f"# Could not extract source for {t_name}: {e}\n")

            # --- 4. sdk metadata ---
            os.makedirs(os.path.join(temp_dir, 'sdk'))
            with open(os.path.join(temp_dir, 'sdk', 'agentcomet.json'), 'w') as f:
                json.dump({"framework": "AgentComet", "compatible_version": ">=0.1.0"}, f)
                
            # --- 5. requirements.txt ---
            with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
                f.write("agentcomet\n")
                
            # --- 6. agent.state (auto-serialized from self.memory) ---
            if has_state:
                with open(os.path.join(temp_dir, 'agent.state'), 'w') as f:
                    json.dump(self.memory.to_dict(), f)
                    
            # --- 7. Build .uaf archive directly (tar.gz) ---
            import tarfile
            uaf_output = os.path.join(temp_dir, "temp_agent.uaf")
            
            files_to_pack = [
                "agent.yaml",
                "agent.py",
                "requirements.txt",
                "sdk/agentcomet.json"
            ]
            if custom_names:
                files_to_pack.append("tools.py")
            if has_state:
                files_to_pack.append("agent.state")
            
            with tarfile.open(uaf_output, "w:gz") as tar:
                for fname in files_to_pack:
                    fpath = os.path.join(temp_dir, fname)
                    if os.path.exists(fpath):
                        tar.add(fpath, arcname=fname)
            
            # Copy to destination path
            shutil.copy2(uaf_output, path)
            print(f"Exported AgentComet agent '{self.name}' to {path}")

    def push_local(self, version: str = "auto", readme: Optional[str] = None) -> dict:
        """
        Push the agent to a locally hosted AgentComet server.
        """
        import requests
        import tempfile
        import os
        from agentcomet.settings import Settings
        
        url = Settings.get_url()
        key = Settings.get_key()
        
        if not url or not key:
            raise ValueError("AGENTCOMET_LOCAL_URL and AGENTCOMET_LOCAL_KEY must be set to push locally.")
            
        target_version = version
        if version == "auto":
            try:
                resp = requests.get(f"{url}/api/sdk/agents/{self.name}", headers={"Authorization": f"Bearer {key}"}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    current_version = data.get("version", "0.1.0")
                    parts = current_version.split(".")
                    if len(parts) >= 3 and parts[-1].isdigit():
                        parts[-1] = str(int(parts[-1]) + 1)
                        target_version = ".".join(parts)
                    else:
                        target_version = "0.1.1"
                else:
                    target_version = "0.1.0"
            except Exception:
                target_version = "0.1.0"
                
        readme_text = readme if readme is not None else self.description
        
        with tempfile.NamedTemporaryFile(suffix=".uaf", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            self.export(tmp_path, version=target_version)
            
            with open(tmp_path, "rb") as f:
                files = {
                    "artifact": (f"{self.name}.uaf", f, "application/octet-stream")
                }
                data = {
                    "name": self.name,
                    "description": self.description,
                    "version": target_version,
                    "readme": readme_text
                }
                
                push_url = f"{url}/api/sdk/agents/push"
                headers = {"Authorization": f"Bearer {key}"}
                
                resp = requests.post(push_url, headers=headers, data=data, files=files, timeout=60)
                resp.raise_for_status()
                
                print(f"Successfully pushed '{self.name}' v{target_version} to {url}")
                return resp.json()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @classmethod
    def pull_local(cls, agent_name: str, version: str = "latest"):
        """
        Pull an agent from a locally hosted AgentComet server.
        """
        import requests
        import os
        import tempfile
        from agentcomet.settings import Settings
        from agentcomet.agents.loader import load_agent
        
        url = Settings.get_url()
        key = Settings.get_key()
        
        if not url or not key:
            raise ValueError("AGENTCOMET_LOCAL_URL and AGENTCOMET_LOCAL_KEY must be set to pull locally.")
            
        params = {"version": version} if version and version != "latest" else None
        
        pull_url = f"{url}/api/sdk/agents/{agent_name}/pull"
        headers = {"Authorization": f"Bearer {key}"}
        
        resp = requests.get(pull_url, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".uaf", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            
            agent = load_agent(tmp_path)
            print(f"Successfully pulled and loaded '{agent_name}' v{version}")
            return agent
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


