"""FastAPI host: exposes the agent as a web UI plus an OpenAI-compatible endpoint."""
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .agent_loop import AgentLoop
from .common import load_config
from .llm_client import LLMClient
from .registry import PluginRegistry


def create_app():
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    client = LLMClient(
        base_url=llm_cfg.get("base_url", "http://localhost:1234"),
        model=llm_cfg.get("model", "local-model"),
        api_key=llm_cfg.get("api_key", ""),
        timeout=llm_cfg.get("timeout_seconds", 180),
    )
    registry = PluginRegistry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins"))
    loop = AgentLoop(client, registry, cfg.get("agent", {}).get("max_iterations", 40))

    app = FastAPI(title="Agent Hero — universal local agent host")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "llm_base_url": client.base_url,
            "model": client.model,
            "llm_reachable": client.ping(),
            "tools_loaded": len(registry.plugins),
        }

    @app.get("/tools")
    def tools():
        return {"plugins": registry.manifests, "tool_count": len(registry.plugins)}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        """OpenAI-compatible endpoint. Runs the full agent loop and returns the final answer."""
        body = await request.json()
        messages = body.get("messages", [])
        if not messages:
            return JSONResponse({"error": "no messages provided"}, status_code=400)
        result = loop.run(messages, system_prompt=body.get("system_prompt"))
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": client.model,
            "choices": [
                {"message": {"role": "assistant", "content": result["final_answer"]}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "agent_trace": result["trace"],
        }

    @app.post("/agent/run")
    async def agent_run(request: Request):
        body = await request.json()
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "prompt is required"}, status_code=400)
        result = loop.run([{"role": "user", "content": prompt}])
        return {"final_answer": result["final_answer"], "steps": result["steps"], "trace": result["trace"]}

    @app.get("/")
    def index():
        return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui", "index.html"))

    return app
