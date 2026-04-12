# Changelog

All notable changes to AgentComet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-beta] — 2026-03-30

### 🎉 Initial Release

The first public beta of AgentComet — a modern Python SDK for building stateful, portable, and composable AI agents.

### Added

#### Agent Core
- `Agent` class with declarative `setup()` override pattern for subclass configuration
- `agent.run(input)` / `agent.chat(input)` — full tool-calling loop with automatic memory tracking
- `agent.invoke(state)` — LangGraph-compatible dict-based entry point
- `agent.use_llm(model)` — hot-swap LLM backends at runtime (supports instance or shorthand strings like `"ollama:gemma3:4b"`)
- `agent.add_tools(*tools)` — register custom tools into the agent's internal registry
- `create_agent()` — declarative one-liner factory for creating agents without subclassing

#### Tool System
- `@tool` decorator — auto-generates name, JSON schema, and description from type hints and docstrings
- `ToolSpec` wrapper class — callable with embedded schema metadata
- `ToolRegistry` — internal registry for managing tool lifecycles
- Built-in tools: `read(file_path)` and `write(file_path, content)` — auto-registered on every agent

#### Memory
- `Memory` class — simple key-value store attached to every agent as `self.memory`
- Methods: `save()`, `get()`, `delete()`, `has()`, `keys()`, `clear()`
- Serialization: `to_dict()`, `from_dict()`, `to_json()`, `from_json()`
- Conversation history auto-appended to `memory["messages"]` on every `run()`/`chat()` call

#### State Persistence
- `agent.save_state(name)` — checkpoint entire memory with SHA-256 hash or friendly name
- `agent.load_state(identifier)` — restore by hash, name, or `None` for latest
- `agent.show_states()` — list all saved checkpoints with timestamps and key counts
- `agent.delete_state(identifier)` — remove specific checkpoints
- State stored in `.agentcomet/` directory with JSON index tracking

#### Universal Agent Files (.uaf)
- `agent.export(path, version)` — package agent code, tools, memory, and manifest into a portable `.uaf` archive (gzipped tar)
- `load_agent(path)` — auto-detect SDK type from `agent.yaml` manifest and reconstruct the agent with full memory restoration
- `AgentCometRuntime` — native runtime for loading AgentComet SDK agents from `.uaf`
- `GenericUAFRuntime` — fallback runtime for legacy UAF agents via `uaf-cli`
- UAF archive structure: `agent.yaml`, `agent.py`, `tools.py`, `requirements.txt`, `sdk/agentcomet.json`, `agent.state`

#### Local Registry (Push & Pull)
- `agent.push_local(version, readme)` — push agent to a locally hosted AgentComet Studio server
  - Auto-version: queries server for latest version and increments patch number
  - Multipart upload with name, description, version, readme, and `.uaf` artifact
- `Agent.pull_local(agent_name, version)` — pull and instantiate agent from local registry
- `Settings` class — global configuration for `AGENTCOMET_LOCAL_URL` and `AGENTCOMET_LOCAL_KEY`
  - Programmatic: `Settings.init(**kwargs)`
  - Environment variable fallback: reads from `AGENTCOMET_LOCAL_URL` / `AGENTCOMET_LOCAL_KEY`
- AgentComet Studio Docker image: `vaibhavhaswani/agentcomet-studio:latest`

#### LLM Providers
- `Ollama` — local models via Ollama server (with optional `as_langchain()` interop)
- `OpenAIChat` — GPT-4o, GPT-4, GPT-3.5 (requires `openai`)
- `Gemini` — Google Gemini with auto-detection of `google-genai` (new) or `google-generativeai` (legacy)
- `Anthropic` — Claude models (requires `anthropic`)
- `OpenRouter` — multi-model access via single API
- `Perplexity` — Perplexity AI search-augmented models
- All providers: lazy client initialization, environment variable fallback for API keys, explicit `api_key` parameter support

#### Orchestration (Experimental)
- `AgentOrchestrator` — workflow-based multi-agent execution
- `WorkflowBuilder` — DAG-based agent pipeline definition
- `ExecutionEngine` — topological execution with conditional routing
- `MessageBroker` — inter-agent communication

#### Version Control (Experimental)
- `Repository` — git-like VCS for agent files with commit, log, and diff support

#### CLI (Disabled)
- `afc` command-line tool scaffolded with `init`, `build`, `run`, and `vcs` subcommands
- Currently disabled — use SDK methods directly

### Dependencies
- **Core:** `requests`, `pyyaml`, `uaf-cli`
- **Optional LLM providers:** `openai`, `google-genai`, `anthropic` (install only what you need)
- **Lightweight** — minimal core dependencies, install only what you need

### Notes
- This is a **beta release** — API surface may change before 1.0
- Python 3.8+ required
- Licensed under Apache License 2.0
- Patent: Indian Provisional Patent Application No. 202611013684

---

[0.1.0-beta]: https://github.com/vaibhavhaswani/agentcomet/releases/tag/v0.1.0-beta
