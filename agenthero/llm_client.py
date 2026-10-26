"""Minimal OpenAI-compatible chat client for local LLM servers (e.g. LM Studio)."""
import requests


class LLMClient:
    def __init__(self, base_url="http://localhost:1234", model="local-model", api_key="", timeout=180):
        self.base_url = str(base_url).rstrip("/")
        self.model = model
        self.api_key = api_key or ""
        self.timeout = int(timeout)

    def chat(self, messages, tools=None):
        """Send a conversation (with optional tool schemas) and return the assistant message."""
        payload = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]

    def ping(self):
        """True if the LLM server answers /v1/models."""
        try:
            r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
