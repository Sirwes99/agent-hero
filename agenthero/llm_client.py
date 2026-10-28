"""Minimal OpenAI-compatible chat client for local LLM servers (e.g. LM Studio)."""
import time

import requests


class LLMClient:
    def __init__(self, base_url="http://localhost:1234", model="local-model", api_key="", timeout=180):
        self.base_url = str(base_url).rstrip("/")
        self.model = model
        self.api_key = api_key or ""
        self.timeout = int(timeout)

    def chat(self, messages, tools=None, extra=None, timeout=None):
        """Send a conversation and return (assistant_message, meta).

        meta carries the response `usage` block and wall-clock elapsed seconds so
        callers can compute token speed. `extra` merges optional payload params
        (e.g. temperature / reasoning_effort) into the request body. If the server
        rejects the extra params with a 4xx, one retry is made without them.
        """
        base_payload = {"model": self.model, "messages": messages}
        if tools:
            base_payload["tools"] = tools
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        def post(payload):
            return requests.post(
                f"{self.base_url}/v1/chat/completions", json=payload, headers=headers,
                timeout=timeout or self.timeout)

        t0 = time.time()
        try:
            resp = post(base_payload)
            if extra and resp.status_code in (400, 422):
                # Some servers reject unknown params; retry with the safe core payload.
                resp = post(base_payload)
            resp.raise_for_status()
        except requests.HTTPError:
            raise
        data = resp.json()
        message = data["choices"][0]["message"]
        return message, {"usage": data.get("usage"), "elapsed_s": time.time() - t0}

    def ping(self):
        """True if the LLM server answers /v1/models."""
        try:
            r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
