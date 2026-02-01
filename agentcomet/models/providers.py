import os
import requests
from typing import List, Dict, Optional, Any
from .base_model import BaseLLM

class Ollama(BaseLLM):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": False}
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

class OpenAIChat(BaseLLM):
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. pip install openai")
        
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def generate(self, prompt: str) -> str:
        # Wrapper around chat for simple completion
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return resp.choices[0].message.content

class Gemini(BaseLLM):
    def __init__(self, model: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package is required.")
        
        genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> str:
        resp = self.model.generate_content(prompt)
        return resp.text

    def chat(self, messages: List[Dict[str, str]]) -> str:
        # Trivial mapping; Gemini has history-based chat API but simplified:
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        return self.generate(prompt)

class Anthropic(BaseLLM):
    """Claude models via Anthropic API."""
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is required. pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=messages
        )
        return resp.content[0].text

class OpenRouter(BaseLLM):
    """OpenRouter API - access multiple models via single API."""
    def __init__(self, model: str = "openai/gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages
        }
        resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

class Perplexity(BaseLLM):
    """Perplexity AI API."""
    def __init__(self, model: str = "llama-3.1-sonar-small-128k-online", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages
        }
        resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
