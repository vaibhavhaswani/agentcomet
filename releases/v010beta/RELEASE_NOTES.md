# 🌠 AgentComet v0.1.0-beta — Release Notes

**Release Date:** March 30, 2026
**Status:** Beta (Pre-release)
**Install:** `pip install --pre agentcomet==0.1.0b1`

---

## 🎉 First Public Release

We're excited to introduce **AgentComet** — a modern Python SDK for building AI agents that are stateful, portable, and composable by design.

---

## What's Inside

### 🤖 Agent Framework
Build agents with a clean, declarative API. Override `setup()` to configure tools, metadata, and LLM — or use `create_agent()` for a one-liner.

```python
from agentcomet import Agent, tool
from agentcomet.models import Ollama

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

class MathAgent(Agent):
    def setup(self):
        self.name = "math-bot"
        self.add_tools(multiply)

agent = MathAgent(llm=Ollama(model="gemma3:4b"))
agent.run("What is 6 times 7?")
```

### 🧠 Built-in Memory
Every agent ships with `self.memory` — a key-value store that automatically tracks conversation history. No boilerplate. No manual serialization.

### 💾 State Checkpoints
Save and restore agent timelines with `save_state()` / `load_state()`. Roll back mistakes, branch experiments, audit history — all with a single method call.

### 📦 Universal Agent Files (.uaf)
Package your entire agent — code, tools, memory, and config — into a single portable `.uaf` file. Load it on any machine and resume exactly where you left off.

```python
agent.export("my-agent.uaf")
loaded = load_agent("my-agent.uaf")  # Memory fully restored
```

### ☁️ Local Registry with AgentComet Studio
Push and pull agents to a private registry running on Docker. Auto-versioning, team sharing, and seamless sync — like git, but for agents.

```bash
docker pull vaibhavhaswani/agentcomet-studio:latest
docker run -p 3451:3451 -v $(pwd)/data:/app/data vaibhavhaswani/agentcomet-studio:latest
```

```python
agent.push_local()                          # Auto-increments version
agent = Agent.pull_local("math-bot")        # Pull latest
```

### 🔌 6 LLM Providers
Swap models with a single line. All providers support explicit API keys and environment variable fallback.

| Provider | Example |
|----------|---------|
| Ollama | `Ollama(model="gemma3:4b")` |
| OpenAI | `OpenAIChat(model="gpt-4o")` |
| Gemini | `Gemini(model="gemini-2.0-flash")` |
| Anthropic | `Anthropic(model="claude-sonnet-4-20250514")` |
| OpenRouter | `OpenRouter(model="openai/gpt-4o")` |
| Perplexity | `Perplexity()` |

### 🛠️ Tool System
The `@tool` decorator auto-generates JSON schemas from Python type hints. Built-in `read` and `write` tools are pre-registered on every agent.

---

## Architecture Highlights

- **Lightweight** — minimal core dependencies
- **Core deps:** `requests`, `pyyaml`, `uaf-cli` only
- **Optional LLM packages:** install only the providers you need
- **Python 3.8+** compatible

---

## Experimental Features

These are included but may change significantly before 1.0:

- **Orchestration** — `AgentOrchestrator` for DAG-based multi-agent workflows
- **VCS** — `Repository` for git-like version control of agent files
- **CLI** — `afc` command-line tool (currently disabled, use SDK directly)

---

## Known Limitations

- Ollama provider requires a running Ollama server (`ollama serve`)
- `push_local` / `pull_local` require AgentComet Studio to be running
- The `export()` method requires `uaf-cli` for UAF compilation
- API surface is not yet stabilized — breaking changes possible before 1.0

---

## What's Next

- Agent-to-agent communication protocols
- Global agent registry (public hub)
- Workflow templates and patterns
- Enhanced CLI tooling
- SDK stabilization toward v1.0

---

## Legal

- **License:** Apache License 2.0
- **Patent:** Indian Provisional Patent Application No. 202611013684
- **Trademark:** "AgentComet" is a trademark of Vaibhav Haswani

---

<p align="center">
  <strong>Built with ❤️ by Vaibhav Haswani.</strong><br/>
  <a href="https://github.com/vaibhavhaswani/agentcomet">GitHub</a> · <a href="https://pypi.org/project/agentcomet/">PyPI</a>
</p>
