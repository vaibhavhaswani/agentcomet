import os
from agentcomet.models import Ollama, OpenAIChat, Anthropic, Gemini, OpenRouter, Perplexity

print("--- Testing LLM Initialization & Lazy Loading ---")

# 1. Ollama (Doesn't require external SDK for direct generation)
try:
    ollama = Ollama(model="gemma3:4b")
    print("[Ollama] Initialized")
except Exception as e:
    print(f"[Ollama] Failed: {e}")

# 2. OpenAI
try:
    openai = OpenAIChat(model="gpt-4o", api_key="sk-dummy")
    print("[OpenAI] Initialized with explicit api_key")
except Exception as e:
    print(f"[OpenAI] Failed to Initialize: {e}")

# 3. Gemini
try:
    gemini = Gemini(model="gemini-1.5-flash", api_key="AIza-dummy")
    print("[Gemini] Initialized with explicit api_key")
except Exception as e:
    print(f"[Gemini] Failed to Initialize: {e}")

# 4. Anthropic
try:
    anthropic = Anthropic(model="claude-3-5-sonnet", api_key="sk-ant-dummy")
    print("[Anthropic] Initialized with explicit api_key")
except Exception as e:
    print(f"[Anthropic] Failed to Initialize: {e}")

print("\n--- Testing Lazy Load Exceptions for missing packages ---")

# Try to invoke Gemini to see the deferred load error
print("\nTesting Gemini generation deferred import:")
try:
    gemini.generate("Hello")
except ImportError as ie:
    print(f"Caught expected ImportError:\n{ie}")
except Exception as e:
    print(f"Caught other exception: {e}")

print("\nDone!")
