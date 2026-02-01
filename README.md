<h1 align="center">🌠 AgentComet</h1>

<p align="center">
  <img src="https://img.shields.io/badge/AgentComet-v0.1.0-blueviolet?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"/>
  <img src="https://img.shields.io/badge/LangGraph-Compatible-orange?style=for-the-badge" alt="LangGraph"/>
</p>

<p align="center">
  <strong>The First Version Control System for AI Agents</strong><br/>
  <em>Modern orchestration. Simplified workflows. Git-like versioning for .uaf agents.</em>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-why-agentcomet">Why AgentComet?</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-examples">Examples</a>
</p>


---

## 🎯 What is AgentComet?

AgentComet is **the only solution** that combines:

- 🗂️ **Agent Version Control** — Git-like VCS built specifically for AI agent binaries (.uaf files)
- 🔄 **Modern Orchestration** — Connect agents with 3 lines of code
- 💬 **Simplified API** — Plain text in, plain text out. No message format juggling
- 🧠 **Built-in Memory** — Conversation history with full or sliding window modes
- ⚡ **Hot Reloading** — Update agent logic without restarting

```python
from agentcomet.agents import UAFAgent

agent = UAFAgent("assistant", "agent.uaf", llm=llm, memory="full")
response = agent.invoke("What is 2 + 2?")
print(response.content)  # "4"
```

---

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| **Supported LLM Providers** | 6+ (Ollama, OpenAI, Gemini, Anthropic, OpenRouter, Perplexity) |
| **Workflow Patterns** | 3 (Pipeline, Fan-Out/Fan-In, Map-Reduce) |
| **Memory Modes** | 3 (None, Full, Sliding Window) |
| **CLI Commands** | 5 (init, build, run, vcs commit, vcs log) |
| **Core Modules** | 6 (agents, orchestrators, workflows, vcs, models, communication) |

---

## 🚀 Quick Start

### Installation

```bash
# Install from source
pip install -e .

# Dependencies
pip install uaf_compiler langchain-ollama
```

### Your First Agent

```python
from langchain_ollama import ChatOllama
from agentcomet.agents import UAFAgent

# 1. Configure LLM
llm = ChatOllama(base_url="http://localhost:11434", model="gemma3:4b")

# 2. Load agent with memory
agent = UAFAgent("my_agent", "path/to/agent.uaf", llm=llm, memory="full")

# 3. Chat naturally
response = agent.invoke("Explain quantum computing in simple terms")
print(response.content)

# 4. Follow-up (agent remembers context!)
response = agent.invoke("Can you give an example?")
print(response.content)
```

---

## ✨ Features

### 🎭 Simplified Agent API
No more wrestling with message formats. Just pass text, get text back.

```python
# Before (raw LangGraph)
result = agent.invoke({"messages": [HumanMessage(content="Hello")]})
output = result["messages"][-1].content

# After (AgentComet)
response = agent.invoke("Hello")
print(response.content)
```

### 🧠 Intelligent Memory

```python
# Full memory - remembers everything
agent = UAFAgent("chat", path, llm=llm, memory="full")

# Last 5 messages only
agent = UAFAgent("chat", path, llm=llm, memory=5)

# Manage history
agent.get_history()    # View messages
agent.clear_memory()   # Reset conversation
```

### 🔗 Multi-Agent Orchestration

```python
from agentcomet.orchestrators import AgentOrchestrator

orch = AgentOrchestrator(llm=llm)
orch.add_agent('researcher', 'research.uaf')
orch.add_agent('writer', 'write.uaf')
orch.add_agent('editor', 'edit.uaf')

orch.connect('researcher', 'writer')
orch.connect('writer', 'editor')

result = orch.run(initial_state)
```

### 📋 Workflow Templates

```python
from agentcomet.workflows import WorkflowTemplates

# Linear pipeline
workflow = WorkflowTemplates.pipeline({
    'step1': 'agent1.uaf',
    'step2': 'agent2.uaf',
    'step3': 'agent3.uaf'
})

# Parallel fan-out/fan-in
workflow = WorkflowTemplates.fan_out_fan_in(
    start_agent={'dispatcher': 'dispatch.uaf'},
    parallel_agents={'w1': 'worker.uaf', 'w2': 'worker.uaf'},
    end_agent={'aggregator': 'aggregate.uaf'}
)
```

### 🗂️ Agent Version Control

The **first and only** VCS designed for AI agents.

```bash
# CLI
afc vcs init
afc vcs commit -m "Initial agent release" agent.uaf
afc vcs log
```

```python
# Python API
from agentcomet.vcs import Repository

repo = Repository()
repo.init()
repo.commit("Add reasoning agent v1.0", ["agents/reasoner.uaf"])
repo.log()
```

### ⚡ Hot Reloading

Update agents without restarting your application:

```python
agent.reload()  # Reloads from .uaf file, preserves memory
```

### 🔌 Multiple LLM Providers

```python
from agentcomet.models import (
    Ollama,       # Local models
    OpenAIChat,   # GPT-4, GPT-4o
    Gemini,       # Google Gemini
    Anthropic,    # Claude
    OpenRouter,   # 100+ models
    Perplexity    # Search-augmented
)

# Mix and match per agent
orch.add_agent('analyst', 'analyze.uaf', llm=Anthropic())
orch.add_agent('coder', 'code.uaf', llm=OpenAIChat())
```

---

## 🤔 Why AgentComet?

| Problem | Traditional Approach | AgentComet Solution |
|---------|---------------------|---------------------|
| **Agent Versioning** | Manual file management | Git-like VCS with SHA-256 integrity |
| **Message Formats** | Wrap everything in `HumanMessage` | Plain text in/out |
| **Memory** | Build your own | Built-in `memory="full"` or `memory=N` |
| **Multi-Agent** | Complex graph APIs | `add_agent()` + `connect()` |
| **Hot Updates** | Restart everything | `agent.reload()` |
| **LLM Switching** | Refactor code | Change `llm=` parameter |

---

## 📖 API Reference

### UAFAgent

```python
UAFAgent(
    name: str,           # Agent identifier
    uaf_path: str,       # Path to .uaf file
    llm: Any = None,     # LLM instance
    memory: str|int = None  # "full", N, or None
)

# Methods
agent.invoke(text) -> AgentResponse  # Run agent
agent.reload()                        # Hot-reload
agent.get_history() -> List           # Get messages
agent.clear_memory()                  # Reset history
agent.cleanup()                       # Clean temp files
```

### AgentResponse

```python
response.content   # str - Plain text output
response.messages  # List - Full message history  
response.raw       # Dict - Original state dict
```

### AgentOrchestrator

```python
AgentOrchestrator(workflow=None, llm=None)

orch.add_agent(name, path, llm=None)
orch.connect(start, end)
orch.run(initial_state) -> Dict
```

### WorkflowTemplates

```python
WorkflowTemplates.pipeline(agents_map)
WorkflowTemplates.fan_out_fan_in(start, parallel, end)
WorkflowTemplates.map_reduce(mapper, workers, reducer)
```

### Repository (VCS)

```python
repo = Repository(path)
repo.init()
repo.commit(message, files, author="Unknown")
repo.log()
```

---

## 📁 Project Structure

```
agentcomet/
├── agents/          # UAFAgent, AgentResponse
├── orchestrators/   # AgentOrchestrator, ExecutionEngine
├── workflows/       # WorkflowBuilder, Templates, Patterns
├── models/          # LLM providers (Ollama, OpenAI, etc.)
├── vcs/             # Repository, version control
├── communication/   # MessageBroker (experimental)
└── cli.py           # afc command-line tool
```

---

## 🛠️ CLI Commands

```bash
afc init <name>              # Create new agent project
afc build --setup file.yaml  # Compile to .uaf
afc run agent.uaf            # Execute agent
afc vcs init                 # Initialize repository
afc vcs commit -m "msg" file # Commit agents
afc vcs log                  # View history
```

---

## 🔗 Related Projects

- **[UAF Compiler](https://github.com/vaibhavhaswani/UAF-Compiler)** — Compile agents to portable .uaf format

---

## 📄 License

Apache License 2.0

---

<p align="center">
  <strong>Built for the future of AI agents</strong><br/>
  <em>⭐ Star this repo if you find it useful!</em>
</p>
