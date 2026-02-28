import os
import tempfile
import json
from typing import Any, Dict, List, Optional, Union
from agentcomet.agents.base_agent import BaseAgent
from agentcomet.models.base_model import BaseLLM
from agentcomet.tools import ToolSpec, ToolRegistry, default_registry

class Agent(BaseAgent):
    """
    Agent class for AgentComet SDK providing declarative setup and tools.
    """
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None, author: Optional[str] = None, llm: Optional[Union[str, BaseLLM]] = None):
        self.description = description or "This is a tool calling agent that solves tasks using its assigned tools."
        self.author = author or "AgentComet"
        self._llm_provider = None
        self._llm_instance = None
        self._memory_enabled = False
        self.registry = ToolRegistry()
        
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
        
    def use_llm(self, model: Union[str, BaseLLM]):
        """Configure the LLM provider. Accepts a BaseLLM instance or a string like 'ollama:gemma3:4b'."""
        if isinstance(model, BaseLLM):
            self._llm_instance = model
            # Derive a provider string for serialization
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
        """Enable or disable memory for the agent."""
        self._memory_enabled = enabled
        
    def add_tools(self, *tools: ToolSpec):
        """Add tools to the agent's registry."""
        for tool in tools:
            self.registry.register_agent_tool(tool)
            
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Base implementation from BaseAgent. Wraps chat."""
        # Simple implementation, extract input and call chat
        user_input = state.get("input", "")
        if not user_input and "messages" in state:
            messages = state["messages"]
            if messages:
                user_input = messages[-1].content
        
        response = self.chat(user_input)
        return {"output": response}

    def chat(self, input: str) -> str:
        """Core method to invoke the model."""
        tools_list = [t.name for t in self.registry.get_all_tools()]
        
        if hasattr(self, '_llm_instance') and self._llm_instance:
            try:
                prompt = f"Available Tools: {tools_list}\nUser Query: {input}"
                return self._llm_instance.generate(prompt)
            except Exception as e:
                return f"[Agent: {self.name}] Error invoking LLM {self._llm_provider}: {e}"
                
        return f"[Agent: {self.name}] LLM: {self._llm_provider}. Tools: {tools_list}. Input: {input}"

    def run(self, input: str) -> str:
        """Run the agent."""
        return self.chat(input)

    def export(self, path: str):
        """
        Export the Agent into a UAF format using the v2 Manifest structure.
        """
        import tempfile
        import shutil
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Provide minimal requirements
            # 2. Extract specific module imports if custom tools have it (naive approach for now)
            
            # --- 1. agent.yaml (V2 Manifest) ---
            builtin_tools = []
            custom_tools = []
            
            for t_name, t_spec in self.registry.builtin_tools.items():
                if t_name in self.registry.agent_tools:
                    builtin_tools.append(t_name)
                    
            for t_name, t_spec in self.registry.agent_tools.items():
                if t_name not in self.registry.builtin_tools:
                    custom_tools.append(t_name)
                    
            # If default builtins haven't explicitly been overridden in agent_tools,
            # but they exist, we just check what's actually configured.
            # A cleaner way is just listing all registered agent tools. We'll dump all for simplicity.
            all_t = self.registry.get_all_tools()
            builtin_names = [t.name for t in all_t if t.name in default_registry.builtin_tools]
            custom_names = [t.name for t in all_t if t.name not in default_registry.builtin_tools]

            manifest = {
                "uaf_version": 2,
                "agent": {
                    "name": self.name,
                    "version": "0.1.0",
                    "description": self.description,
                    "author": self.author
                },
                "runtime": {
                    "engine": "python",
                    "entrypoint": "agent:agent" # We'll expose the agent instance as 'agent'
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
                    "enabled": self._memory_enabled,
                    "file": "agent.state" if self._memory_enabled else None
                },
                "dependencies": {
                    "auto": True
                }
            }
            
            # Cleanup nulls from State
            if not manifest["state"]["file"]:
                del manifest["state"]["file"]
                
            with open(os.path.join(temp_dir, 'agent.yaml'), 'w') as f:
                # Basic YAML dumping
                import yaml
                yaml.dump(manifest, f, sort_keys=False)
                
            # --- 2. agent.py (Generic runner) ---
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
                    # NOTE: This implies they are imported.
                    f.write(f"    tools={tool_list_str},\n")
                f.write(f"    memory={self._memory_enabled}\n")
                f.write(")\n")
                
            # --- 3. tools.py (Custom Tools Optional) ---
            if custom_names:
                with open(os.path.join(temp_dir, 'tools.py'), 'w') as f:
                    f.write("from agentcomet.tools import tool\n\n")
                    # Naively try to extract source utilizing inspect
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
                
            # --- 6. agent.state ---
            if self._memory_enabled:
                with open(os.path.join(temp_dir, 'agent.state'), 'w') as f:
                    json.dump({"messages": [], "memory_mode": "full"}, f)
                    
            # --- 7. Setup Builder yaml ---
            files_map = {
                "agent.yaml": "agent.yaml",
                "agent.py": "agent.py",
                "requirements.txt": "requirements.txt",
                "sdk/agentcomet.json": "sdk/agentcomet.json"
            }
            if custom_names:
                files_map["tools.py"] = "tools.py"
            if self._memory_enabled:
                files_map["agent.state"] = "agent.state"
            
            # Write setup yaml
            with open(os.path.join(temp_dir, 'uaf_setup.yaml'), 'w') as f:
                import yaml
                yaml.dump({"output": "temp_agent.uaf", "files": files_map}, f)
                    
            # Compile using UAF Builder
            from uaf_compiler.builder import UAFBuilder
            builder = UAFBuilder(setup_file="uaf_setup.yaml", target_dir=temp_dir)
            builder.build()
            
            # Copy to destination path
            import shutil
            shutil.copy2(os.path.join(temp_dir, "temp_agent.uaf"), path)
            print(f"Exported AgentComet agent {self.name} to {path}")
