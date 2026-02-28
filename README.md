<h1 align="center">🌠 AgentComet</h1>

<p align="center">
  <img src="https://img.shields.io/badge/AgentComet-v0.1.0-blueviolet?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/UAF-v2-orange?style=for-the-badge" alt="UAF v2"/>
</p>

<p align="center">
  <strong>Write your first portable AI agent in a few lines of code.</strong><br/>
  <em>SDK-first. Tool calling. Export anywhere. No lock-in.</em>
</p>

---

## 🎯 What is AgentComet?

AgentComet is an SDK for building AI agents that are **portable by default**. Define tools, write agent logic, and export to a single `.uaf` file you can share, version, or deploy anywhere.

```python
from agentcomet import Agent
from agentcomet.models import Ollama
from agentcomet.tools import tool

llm = Ollama(model="gemma3:4b")

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

class MathAgent(Agent):
    def setup(self):
        self.name = "math-bot"
        self.add_tools(multiply)

agent = MathAgent(llm=llm)
agent.run("What is 6 times 7?")
agent.export("math-bot.uaf")  # That's it. Portable.
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
        self.use_memory(True)
        self.add_tools(greet)

agent = GreeterAgent(llm=llm)
print(agent.run("Say hello to Alice"))
```

### Export & Load

```python
from agentcomet import load_agent

# Export
agent.export("greeter.uaf")

# Load — anywhere, anytime
loaded = load_agent("greeter.uaf")
loaded.run("Say hello to Bob")
```

The `.uaf` archive is a self-contained `tar.gz`:

```
greeter.uaf
├── agent.yaml         # V2 manifest (sdk: agentcomet)
├── agent.py           # Auto-generated runner
├── tools.py           # Your custom tools
├── requirements.txt
└── sdk/agentcomet.json
```

No LangChain references. No engine leakage. Just your agent.

---

## ✨ Key Features

| Feature | |
|---|---|
| **`@tool` decorator** | Auto-generates name, description, and JSON schema from type hints |
| **Builtin tools** | `read`, `write` — ready to use out of the box |
| **`create_agent()`** | One-liner declarative agent creation (no subclass needed) |
| **UAF export** | `agent.export("file.uaf")` — portable agent archives |
| **UAF load** | `load_agent("file.uaf")` — auto-routes to correct runtime |
| **Memory** | `"full"` or sliding window (`memory=5`) |
| **State persistence** | `save_state()` / `load_state(hash)` — versioned rollback |
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

All providers are passed directly to agents — no `.as_langchain()` needed.

---

## 📖 API at a Glance

```python
# Agent lifecycle
llm = Ollama(model="gemma3:4b")
agent = MyAgent(llm=llm)
agent.run("query")
agent.export("agent.uaf")

# Load from .uaf
agent = load_agent("agent.uaf")

# Declarative shorthand
agent = create_agent(name="bot", llm=llm, tools=[my_tool], memory=True)

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
