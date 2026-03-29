import os
import requests
from typing import List, Dict, Optional, Any
from .base_model import BaseLLM

class Ollama(BaseLLM):
    """
    Ollama LLM provider — local models via Ollama.
    
    Usage:
        llm = Ollama(model="gemma3:4b")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434", temperature: float = 0):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self._langchain_llm = None

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
    
    def invoke(self, input_data: Any) -> Any:
        """LangChain-compatible invoke method."""
        if isinstance(input_data, str):
            return self.generate(input_data)
        
        if isinstance(input_data, list):
            messages = []
            for msg in input_data:
                if hasattr(msg, 'content') and hasattr(msg, 'type'):
                    role = "user" if msg.type == "human" else "assistant"
                    messages.append({"role": role, "content": msg.content})
                elif isinstance(msg, dict):
                    messages.append(msg)
            return self.chat(messages)
        
        if isinstance(input_data, dict) and "messages" in input_data:
            return self.invoke(input_data["messages"])
        
        return self.generate(str(input_data))
    
    def as_langchain(self):
        """Get a LangChain-compatible ChatOllama instance."""
        if self._langchain_llm is None:
            try:
                from langchain_ollama import ChatOllama
                self._langchain_llm = ChatOllama(
                    base_url=self.base_url,
                    model=self.model,
                    temperature=self.temperature
                )
            except ImportError:
                raise ImportError("langchain-ollama is required. pip install langchain-ollama")
        return self._langchain_llm


class OpenAIChat(BaseLLM):
    """
    OpenAI LLM provider (GPT-4o, GPT-4, GPT-3.5, etc.)
    
    Usage:
        llm = OpenAIChat(model="gpt-4o", api_key="sk-...")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")
            
            if not self._api_key:
                raise ValueError("OpenAI API key required. Pass api_key= or set OPENAI_API_KEY env variable.")
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return resp.choices[0].message.content


class Gemini(BaseLLM):
    """
    Google Gemini LLM provider.
    
    Supports both google-genai (new) and google-generativeai (legacy).
    
    Usage:
        llm = Gemini(model="gemini-2.0-flash", api_key="AIza...")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "gemini-2.0-flash", api_key: Optional[str] = None):
        self.model_name = model
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self._client = None
        self._backend = None  # "new" or "legacy"

    def _get_client(self):
        if self._client is not None:
            return self._client
        
        if not self._api_key:
            raise ValueError("Gemini API key required. Pass api_key= or set GOOGLE_API_KEY env variable.")
        
        # Try new SDK first (google-genai)
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
            self._backend = "new"
            return self._client
        except ImportError:
            pass
        
        # Fall back to legacy SDK (google-generativeai)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self.model_name)
            self._backend = "legacy"
            return self._client
        except ImportError:
            pass
        
        raise ImportError(
            "Google AI SDK required. Install with:\n"
            "  pip install google-genai          (recommended)\n"
            "  pip install google-generativeai   (legacy)"
        )

    def generate(self, prompt: str) -> str:
        client = self._get_client()
        if self._backend == "new":
            resp = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return resp.text
        else:
            # Legacy SDK
            resp = client.generate_content(prompt)
            return resp.text

    def chat(self, messages: List[Dict[str, str]]) -> str:
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        return self.generate(prompt)


class Anthropic(BaseLLM):
    """
    Anthropic Claude LLM provider.
    
    Usage:
        llm = Anthropic(model="claude-sonnet-4-20250514", api_key="sk-ant-...")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: Optional[str] = None):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError("anthropic package is required. Install with: pip install anthropic")
            
            if not self._api_key:
                raise ValueError("Anthropic API key required. Pass api_key= or set ANTHROPIC_API_KEY env variable.")
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_client()
        resp = client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=messages
        )
        return resp.content[0].text


class OpenRouter(BaseLLM):
    """
    OpenRouter API — access multiple models via single API.
    
    Usage:
        llm = OpenRouter(model="openai/gpt-4o", api_key="sk-or-...")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "openai/gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key required. Pass api_key= or set OPENROUTER_API_KEY env variable.")
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
    """
    Perplexity AI API.
    
    Usage:
        llm = Perplexity(model="llama-3.1-sonar-small-128k-online", api_key="pplx-...")
        llm.generate("Hello")
    """
    def __init__(self, model: str = "llama-3.1-sonar-small-128k-online", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"

    def generate(self, prompt: str) -> str:
        return self.chat([{"role": "user", "content": prompt}])

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("Perplexity API key required. Pass api_key= or set PERPLEXITY_API_KEY env variable.")
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
