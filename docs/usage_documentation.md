# AgentComet SDK Documentation

AgentComet is a modern framework for building and persisting intelligent agents with robust state management.

---

## 🚀 Quick Start

### Installation
```bash
pip install agentcomet
```

### Basic Usage
```python
from agentcomet import create_agent
from agentcomet.models import Ollama

# 1. Initialize an LLM
llm = Ollama(model="gemma3:4b")

# 2. Create an agent
agent = create_agent(
    name="helper",
    description="A simple assistant",
    llm=llm
)

# 3. Run the agent
response = agent.run("Hello! Who are you?")
print(response)
```

---

## 🛠️ Core Features

### 1. Tools (`@tool`)
The `@tool` decorator converts any Python function into a `ToolSpec` with auto-extracted name, description, and JSON schema.

```python
from agentcomet import Agent, tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers together."""
    return a * b

# Usage in Agent setup
class MyAgent(Agent):
    def setup(self):
        self.add_tools(multiply)
```

> **Note:** AgentComet also provides builtin tools like `read` and `write` (found in `agentcomet.tools`) for direct file operations.

### 2. Memory & Conversations
Every agent has built-in `self.memory`. Conversation history is automatically saved to `memory["messages"]`.

- **Auto-saved chat**: `agent.run()` automatically appends to history.
- **Key-Value Storage**: Store arbitrary structured data.
  ```python
  agent.memory.save("user_prefs", {"theme": "dark"})
  prefs = agent.memory.get("user_prefs")
  print(agent.memory.keys()) # ['messages', 'user_prefs']
  ```

### 3. State Persistence
Snapshots of an agent's memory (including full conversation history) can be saved as named or hashed checkpoints.

```python
agent.save_state("before-deadline-update")
agent.run("Update deadline to March 20th")
agent.save_state("after-deadline-update")

# Rollback anytime
agent.load_state("before-deadline-update")
agent.show_states() # View all checkpoints
```

### 4. UAF Export & Load
Export your agent to a portable `.uaf` format. The exported file includes the agent's code, configuration, and its current memory state.

```python
# Export
agent.export("my_assistant.uaf")

# Load later (restores memory and tools)
from agentcomet import load_agent
loaded = load_agent("my_assistant.uaf")
```

### 5. Agent Registry (Local Server)
Sync your agents with a locally hosted AgentComet server. The SDK automates generating the portable UAF and managing semantic versions.

#### Configuration
First, initialize the connection settings (via code or environment variables):
```python
from agentcomet import Settings

Settings.init(
    AGENTCOMET_LOCAL_URL="http://localhost:3451",
    AGENTCOMET_LOCAL_KEY="your-local-key"
)
```

#### Pushing an Agent
The `push_local` method creates a dynamic UAF and uploads it. Set `version="auto"` to automatically increment the version number.
```python
# Push current agent to the registry
push_res = agent.push_local(version="auto", readme="Initial version")
print(f"Pushed: {push_res['version']['version']}")
```

#### Pulling an Agent
Pull any agent by name. It downloads the UAF and instantiates it instantly.
```python
from agentcomet import Agent

# Pull and load the latest version
downloaded_agent = Agent.pull_local("assistant", version="latest")
print(f"Loaded: {downloaded_agent.name}")
```

---

## 📖 API Reference

### `Agent` Class
The primary class for building agents. Can be subclassed or instantiated via `create_agent`.

| Method | Description | Parameters |
|:-------|:------------|:-----------|
| `setup()` | Configuration hook for subclasses. | - |
| `add_tools(*tools)` | Registers one or more `@tool` functions. | `*tools: ToolSpec` |
| `run(input)` | Sends a message to the agent and returns the response. | `input: str` |
| `save_state(name)` | Creates a memory snapshot. | `name: str` (optional) |
| `load_state(id)` | Restores memory from a hash or name. | `id: str` (optional, defaults to latest) |
| `show_states()` | Lists all available checkpoints. | - |
| `export(path, ver)` | Saves agent as a `.uaf` package. | `path: str`, `ver: str` (default: "0.1.0") |
| `push_local(ver)` | Pushes agent to a local AgentComet server. | `ver: str` (default: "auto") |
| `pull_local(name, ver)` | **(Class Method)** Pulls agent from local server. | `name: str`, `ver: str` (default: "latest") |

### Global Functions & Configuration
| Component | Type | Description |
|:----------|:-----|:------------|
| `create_agent` | Function | Declarative helper to create an Agent instance without subclassing. |
| `load_agent` | Function | Loads a portable agent from a `.uaf` file, restoring its full state. |
| `tool` | Decorator | Converts a standard Python function into a `ToolSpec`. |
| `Settings.init` | Method | Configures `AGENTCOMET_LOCAL_URL` and `AGENTCOMET_LOCAL_KEY`. |

---

## 🤖 LLM Providers

Pass LLM instances directly to your agents during initialization.

- **Ollama (Local)**: `Ollama(model="gemma3:4b")`
- **OpenAI**: `OpenAIChat(model="gpt-4o")`
- **Google**: `Gemini(model="gemini-1.5-flash")`
- **Anthropic**: `Anthropic(model="claude-3-5-sonnet")`
- **Others**: `OpenRouter`, `Perplexity`
