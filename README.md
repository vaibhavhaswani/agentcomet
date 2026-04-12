<h1 align="center">🌠 AgentComet</h1>

<p align="center">
  <img src="https://img.shields.io/badge/AgentComet-v0.1.0_beta-blueviolet?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/UAF-v2-orange?style=for-the-badge" alt="UAF v2"/>
</p>

<p align="center">
  <strong>Build once. Run anywhere. Resume anytime.</strong><br/>
  <em>Stateful. Portable. Composable AI agents.</em>
</p>

---

## ⚡ The Problem

Every AI team ends up rebuilding the same agents.

Same logic. Same tools.
Different environment. New framework.

And the worst part? **All the memory, context, and progress is lost.**
Agents today are stateless, fragile, and non-portable.

---

## 🚀 Introducing AgentComet

AgentComet is a modern agent framework designed to make agents:
- **Stateful by default**
- **Portable across environments**
- **Resumable at any point in time**

Instead of treating agents like scripts, AgentComet treats them like **artifacts**.

---

## 🎯 What makes AgentComet different?

AgentComet introduces a new primitive: **Portable, Stateful Agent Artifacts (`.uaf`)**

You don't just write agents. You package, move, version, and resume them.

---

## 🚀 Quick Start

### Installation

```bash
pip install agentcomet
```

### Build an Agent

Create an agent, assign it custom tools, and let it handle the heavy lifting.

```python
from agentcomet import Agent, tool
from agentcomet.models import Ollama

@tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

class GreeterAgent(Agent):
    def setup(self):
        self.name = "greeter"
        self.add_tools(greet)

# Instantiate and chat
agent = GreeterAgent(llm=Ollama(model="llama3"))
print(agent.run("Say hello to Alice!"))
```

---

## ✨ Core Capabilities

### 🧠 Persistent Memory

Every agent comes with a highly flexible key-value memory store (`self.memory`). Conversational history is **auto-saved** without any manual boilerplate.

```python
agent.memory.save("user_preferences", {"theme": "dark"})
print(agent.memory.get("messages"))
```

### 💾 State Checkpoints

Save and restore exact agent timelines. Need to rollback a prompt mistake? Just load the state.

```python
agent.save_state("checkpoint-1")
agent.load_state("checkpoint-1")
```

### 📦 Portable Agents with .uaf

Stop writing boilerplate to serialize agent code. Export your entire agent—along with its memory, history, LLM config, and tools—into a portable `.uaf` archive.

```python
agent.export("assistant.uaf")

from agentcomet import load_agent
agent = load_agent("assistant.uaf")
```

### ☁️ Local Registry (Push & Pull)

Sync your agents with a locally hosted AgentComet Studio registry. Version, share, and pull agents across your team — like git, but for agents.

#### 1. Start AgentComet Studio

```bash
docker pull vaibhavhaswani/agentcomet-studio:latest

docker run -p 3451:3451 \
  -v $(pwd)/data:/app/data \
  vaibhavhaswani/agentcomet-studio:latest
```

> **Windows (PowerShell):**
> ```powershell
> docker run -p 3451:3451 -v ${PWD}/data:/app/data vaibhavhaswani/agentcomet-studio:latest
> ```

#### 2. Configure the SDK

```python
from agentcomet import Settings

Settings.init(
    AGENTCOMET_LOCAL_URL="http://localhost:3451",
    AGENTCOMET_LOCAL_KEY="your-secret-key"
)
```

Or set environment variables:
```bash
export AGENTCOMET_LOCAL_URL=http://localhost:3451
export AGENTCOMET_LOCAL_KEY=your-secret-key
```

#### 3. Push & Pull

```python
# Push — auto-increments version
agent.push_local()

# Pull — latest or specific version
agent = Agent.pull_local("greeter")
agent = Agent.pull_local("greeter", version="0.1.2")
```

### 🔌 Multi-Provider LLM Support

Switching your backend is as simple as defining a new class.

```python
from agentcomet.models import OpenAIChat, Gemini, Anthropic, Ollama

agent.use_llm(OpenAIChat(model="gpt-4o"))
```

---

## 🧠 Why this matters

We believe the future of AI is not just models.
It's agents that evolve over time.

Agents that:
- Learn
- Persist
- Move
- Continue

AgentComet is a step toward that future.

---

## 🛣️ Vision

This is just the beginning.

AgentComet is part of a larger vision to build:
- A universal agent format
- A global agent registry
- A composable ecosystem of agents

Where agents are not rewritten, but shared, reused, and extended.

---

## 📚 Documentation

For a detailed look at all features, API methods, schemas, and configurations, check out the comprehensive [Usage Documentation](docs/usage_documentation.md).

---

## 🤝 Contributing

- ⭐ Star the repo
- 🛠️ Break things
- 🚀 Open PRs

All contributions are welcome.

---

## 📄 License & Legal

- **License:** Apache License 2.0
- **Patent:** Indian Provisional Patent Application No. 202611013684
- **Branding:** "AgentComet" is a trademark. See [BRANDING.md](./BRANDING.md).
