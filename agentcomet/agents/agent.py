import os
import tempfile
import json
import hashlib
import ast
import warnings
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
        self.max_rounds = 10     # Maximum tool loop execution rounds
        
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
        expr = self._extract_tool_call_source(response)
        if not expr:
            return None

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                node = ast.parse(expr, mode="eval").body
        except Exception:
            return None

        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            return None

        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                return None
            try:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            except Exception:
                return None

        return node.func.id, kwargs

    def _extract_tool_call_source(self, response: str) -> Optional[str]:
        """Extract the first tool-call expression from a strict TOOL_CALL/tool_code response."""
        markers = ["TOOL_CALL:", "```tool_code"]
        start = -1
        offset = 0

        for marker in markers:
            idx = response.find(marker)
            if idx != -1:
                start = idx + len(marker)
                offset = idx
                break

        if start == -1:
            return None

        if response[:offset].strip():
            return None

        text = response[start:].lstrip()
        if not text:
            return None

        if text.startswith("```"):
            text = text[3:].lstrip()
        if not text or not (text[0].isalpha() or text[0] == "_"):
            return None

        depth = 0
        quote = None
        triple = False
        escaped = False
        end_index = None

        for i, ch in enumerate(text):
            if quote:
                if escaped:
                    escaped = False
                    continue
                if ch == "\\":
                    escaped = True
                    continue
                if triple:
                    if text[i:i + 3] == quote * 3:
                        quote = None
                        triple = False
                    continue
                if ch == quote:
                    quote = None
                continue

            if text[i:i + 3] in ("'''", '"""'):
                quote = text[i]
                triple = True
                continue
            if ch in ("'", '"'):
                quote = ch
                triple = False
                continue
            if ch == "(":
                depth += 1
                continue
            if ch == ")":
                depth -= 1
                if depth == 0:
                    end_index = i + 1
                    break

        if end_index is None:
            return None
        return text[:end_index].strip()
    
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
                
                # Tool-calling loop (up to 10 rounds)
                final_response = ""
                for _ in range(10):
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

    def export(self, path: str, version: str = "0.1.0", dependencies: Optional[List[str]] = None):
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
                if dependencies:
                    for dep in dependencies:
                        f.write(f"{dep}\n")
                
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

    @classmethod
    def get_latest_version(cls, repo: str) -> Optional[str]:
        """
        Query the targeted server to discover the latest version of the agent.
        """
        import requests
        from urllib.parse import urlparse
        from agentcomet.settings import Settings
        
        url = Settings.get_url()
        key = Settings.get_key()
        if not url or not key:
            return None
            
        is_local = False
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if hostname in ("localhost", "127.0.0.1") or hostname.startswith("192.168.") or hostname.startswith("10."):
                is_local = True
        except Exception:
            pass
            
        headers = {"Authorization": f"Bearer {key}"}
        try:
            if is_local:
                # Query local pull endpoint using stream=True to read only headers
                pull_url = f"{url}/api/sdk/agents/pull"
                resp = requests.get(pull_url, headers=headers, params={"repo": repo}, stream=True, timeout=5)
                version = resp.headers.get("X-AgentComet-Version")
                resp.close()
                if version:
                    return version
            else:
                # Query remote Hub metadata endpoint
                repo_clean = repo.strip("/")
                if "/" in repo_clean:
                    owner, _, name = repo_clean.partition("/")
                    metadata_url = f"{url}/api/sdk/agents/{owner}/{name}"
                else:
                    metadata_url = f"{url}/api/sdk/agents/{repo_clean}"
                resp = requests.get(metadata_url, headers=headers, timeout=5)
                if resp.ok:
                    return resp.json().get("version")
        except Exception:
            pass
        return None

    def push(self, repo: str, version: str = "auto", create: bool = False, readme: str = None, local: Optional[bool] = None, dependencies: Optional[List[str]] = None) -> dict:
        """
        Push the agent to an AgentComet repository.
        """
        import requests
        import tempfile
        import os
        from urllib.parse import urlparse
        from agentcomet.settings import Settings
        
        url = Settings.get_url()
        key = Settings.get_key()
        
        if not url or not key:
            raise ValueError("AGENTCOMET_URL and AGENTCOMET_KEY must be set in Settings to push.")
            
        # Dynamically detect if we are targeting a local server or public hub
        is_local = False
        if url:
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname or ""
                if hostname in ("localhost", "127.0.0.1") or hostname.startswith("192.168.") or hostname.startswith("10."):
                    is_local = True
            except Exception:
                pass

        use_local_storage = is_local if local is None else local
            
        target_version = version
        if version == "auto":
            try:
                latest = self.get_latest_version(repo)
                if latest:
                    # Increment the version
                    parts = latest.split(".")
                    if len(parts) == 3:
                        try:
                            patch = int(parts[2])
                            target_version = f"{parts[0]}.{parts[1]}.{patch + 1}"
                        except ValueError:
                            target_version = "0.1.0"
                    elif len(parts) == 2:
                        try:
                            minor = int(parts[1])
                            target_version = f"{parts[0]}.{minor + 1}.0"
                        except ValueError:
                            target_version = "0.1.0"
                    else:
                        target_version = "0.1.0"
                else:
                    target_version = "0.1.0"
            except Exception:
                target_version = "0.1.0"
                
        readme_text = readme if readme is not None else self.description
        
        # Extract repo name for local file saving
        repo_name = repo.split("/")[-1] if "/" in repo else repo
        
        with tempfile.NamedTemporaryFile(suffix=".uaf", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            self.export(tmp_path, version=target_version, dependencies=dependencies)
            
            with open(tmp_path, "rb") as f:
                files = {
                    "artifact": (f"{repo_name}.uaf", f, "application/octet-stream")
                }
                data = {
                    "repo": repo,
                    "repoPath": repo,
                    "repoName": repo_name,
                    "name": repo_name,
                    "description": self.description,
                    "version": target_version,
                    "readme": readme_text,
                    "create": "true" if create else "false",
                    "local": "true" if use_local_storage else "false"
                }
                
                push_url = f"{url}/api/sdk/agents/push"
                headers = {"Authorization": f"Bearer {key}"}
                
                resp = requests.post(push_url, headers=headers, data=data, files=files, timeout=60)
                if not resp.ok:
                    raise RuntimeError(f"Hub push failed with HTTP {resp.status_code}: {resp.text}")
                
                print(f"Successfully pushed '{repo}' to {url}")
                return resp.json()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @classmethod
    def pull(cls, repo: str, version: str = "latest"):
        """
        Pull an agent from an AgentComet repository.
        """
        import requests
        import os
        import tempfile
        from urllib.parse import urlparse
        from agentcomet.settings import Settings
        from agentcomet.agents.loader import load_agent
        
        url = Settings.get_url()
        key = Settings.get_key()
        
        if not url or not key:
            raise ValueError("AGENTCOMET_URL and AGENTCOMET_KEY must be set in Settings to pull.")
            
        # Dynamically detect if we are targeting a local server or public hub
        is_local = False
        if url:
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname or ""
                if hostname in ("localhost", "127.0.0.1") or hostname.startswith("192.168.") or hostname.startswith("10."):
                    is_local = True
            except Exception:
                pass

        headers = {"Authorization": f"Bearer {key}"}
        params = {}
        if version and version != "latest":
            params["version"] = version

        if is_local:
            # Local Studio pull route: GET /api/sdk/agents/pull?repo=repo
            pull_url = f"{url}/api/sdk/agents/pull"
            params["repo"] = repo
        else:
            # Remote Hub pull route: /api/sdk/agents/[repo]/pull or /api/sdk/agents/[repo]/[name]/pull
            repo_clean = repo.strip("/")
            if "/" in repo_clean:
                owner, _, name = repo_clean.partition("/")
                pull_url = f"{url}/api/sdk/agents/{owner}/{name}/pull"
            else:
                pull_url = f"{url}/api/sdk/agents/{repo_clean}/pull"
        
        resp = requests.get(pull_url, headers=headers, params=params, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Hub pull failed with HTTP {resp.status_code}: {resp.text}")
        
        with tempfile.NamedTemporaryFile(suffix=".uaf", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            
            agent = load_agent(tmp_path)
            print(f"Successfully pulled and loaded '{repo}'")
            return agent
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
