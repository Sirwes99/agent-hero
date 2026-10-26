"""Minimal OpenAI-compatible client for a local LLM server."""
import requests

class LLMClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages, tools=None) -> dict:
        payload = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
        r = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    def ping(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
