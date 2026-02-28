<h1 align="center">🌠 AgentComet</h1>

<p align="center">
  <img src="https://img.shields.io/badge/AgentComet-v0.1.0-blueviolet?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/UAF-v2-orange?style=for-the-badge" alt="UAF v2"/>
</p>

<p align="center">
  <strong>Build stateful, portable AI agents in a few lines of code.</strong><br/>
  <em>Tool calling. Built-in memory. Export anywhere. No lock-in.</em>
</p>

---

## 🎯 What is AgentComet?

AgentComet is an SDK for building AI agents that are **stateful and portable by default**. Define tools, use key-value memory, and export to a single `.uaf` file — memory included.

```python
from agentcomet import Agent, load_agent
from agentcomet.models import Ollama

llm = Ollama(model="gemma3:4b")

class MyAssistant(Agent):
    def setup(self):
        self.name = "assistant"

agent = MyAssistant(llm=llm)

# Chat — messages auto-saved to memory
agent.run("Hi, I'm Vaibhav. My phone is 9876543210")
agent.run("Remember: project deadline is March 15th")

# Export — conversation auto-packed inside
agent.export("assistant.uaf")

# Later... load and ask from memory
loaded = load_agent("assistant.uaf")
loaded.run("What is my phone number?")   # → "9876543210"
loaded.run("When is the deadline?")       # → "March 15th"
```

---

## 🚀 Quick Start

```bash
pip install -e .
pip install uaf_compiler pyyaml requests
```

### Create Your First Agent

```python
from agentcomet import Agent
from agentcomet.models import Ollama
from agentcomet.tools import tool

llm = Ollama(model="gemma3:4b")

@tool
def greet(name: str) -> str:
    """Greets a person by name."""
    return f"Hello, {name}!"

class GreeterAgent(Agent):
    def setup(self):
        self.name = "greeter"
        self.add_tools(greet)

agent = GreeterAgent(llm=llm)
print(agent.run("Say hello to Alice"))
```

### Memory — Built In

Every agent has `self.memory` — a key-value store that auto-serializes. Store anything: strings, numbers, lists, dicts, conversation history.

```python
# Simple values
agent.memory.save("username", "Alice")
agent.memory.save("task_count", 5)

# Conversation history
agent.memory.save("messages", [
    {"role": "user", "text": "What is 2+2?"},
    {"role": "agent", "text": "The answer is 4."},
    {"role": "user", "text": "Now multiply by 3"},
    {"role": "agent", "text": "4 × 3 = 12."}
])

# Context and notes
agent.memory.save("system_prompt", "You are a helpful math tutor.")
agent.memory.save("summary", "User is learning basic arithmetic.")

print(agent.memory.get("username"))    # "Alice"
print(agent.memory.get("messages"))    # Full conversation history
print(agent.memory.keys())            # ["username", "task_count", "messages", ...]
```

> **Note:** When you call `agent.run()`, messages are automatically appended to `memory["messages"]`. No manual saving needed.

### State Persistence

Save and restore memory snapshots — by auto-hash or friendly name:

```python
hash = agent.save_state()                # -> "a1b2c3d4"
agent.save_state("before-training")       # -> "before-training"

agent.show_states()                       # List all checkpoints
agent.load_state("before-training")       # Restore by name
agent.load_state("a1b2c3d4")             # Restore by hash
agent.load_state()                        # Restore latest
```

### Export & Load

```python
from agentcomet import load_agent

# Export — conversation + memory auto-packed inside
agent.export("assistant.uaf")

# Load — memory auto-restored, agent remembers everything
loaded = load_agent("assistant.uaf")
loaded.run("What was my name again?")   # Answers from stored conversation
```

The `.uaf` archive is a self-contained `tar.gz`:

```
assistant.uaf
├── agent.yaml         # V2 manifest (sdk: agentcomet)
├── agent.py           # Auto-generated runner
├── tools.py           # Your custom tools
├── agent.state        # Memory (auto-serialized JSON)
├── requirements.txt
└── sdk/agentcomet.json
```

---

## ✨ Key Features

| Feature | |
|---|---|
| **`@tool` decorator** | Auto-generates name, description, and JSON schema from type hints |
| **Builtin tools** | `read`, `write` — ready to use out of the box |
| **`create_agent()`** | One-liner declarative agent creation |
| **`self.memory`** | Key-value memory — `save()`, `get()`, `keys()`, `clear()` |
| **State persistence** | `save_state()` / `load_state()` — by hash or friendly name |
| **UAF export** | `agent.export("file.uaf")` — memory auto-packed |
| **UAF load** | `load_agent("file.uaf")` — memory auto-restored |
| **Hot reloading** | `agent.reload()` — update logic without restart |

---

## 🔌 Supported LLM Providers

```python
from agentcomet.models import Ollama, OpenAIChat, Gemini, Anthropic, OpenRouter, Perplexity
```

| Provider | Usage | Requires |
|---|---|---|
| **Ollama** | `Ollama(model="gemma3:4b")` | Local Ollama server |
| **OpenAI** | `OpenAIChat(model="gpt-4o")` | `OPENAI_API_KEY` |
| **Gemini** | `Gemini(model="gemini-1.5-flash")` | `GOOGLE_API_KEY` |
| **Anthropic** | `Anthropic(model="claude-3-5-sonnet")` | `ANTHROPIC_API_KEY` |
| **OpenRouter** | `OpenRouter(model="openai/gpt-4o")` | `OPENROUTER_API_KEY` |
| **Perplexity** | `Perplexity()` | `PERPLEXITY_API_KEY` |

---

## 📖 API at a Glance

```python
# Agent lifecycle
agent = MyAgent(llm=Ollama(model="gemma3:4b"))
agent.run("query")
agent.export("agent.uaf")

# Memory
agent.memory.save("key", value)
agent.memory.get("key")

# State
agent.save_state()                # hash
agent.save_state("checkpoint")    # named
agent.load_state("checkpoint")
agent.show_states()

# Load from .uaf
agent = load_agent("agent.uaf")

# Tools
@tool
def my_func(x: int) -> int:
    """Does something."""
    return x * 2
```

---

## 🔗 Related

- **[UAF Compiler](https://github.com/vaibhavhaswani/UAF-Compiler)** — Compile and validate `.uaf` archives

---

## 📄 License

Apache License 2.0

## ⚖️ Legal & Branding

- **Patent**: Indian Provisional Patent Application No. 202611013684
- **Branding**: "AgentComet" is a trademark. See [BRANDING.md](./BRANDING.md)
- **Attribution**: Redistribution must retain the [NOTICE](./NOTICE) file

<p align="center">
  <strong>Built with ❤️ by Vaibhav Haswani for the future of AI agents.</strong><br/><br/>
  <em>⭐ Star this repo if you find it useful!</em>
</p>
