"""FastAPI web host: serves the UI and exposes OpenAI-compatible endpoints."""
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

WEBUI = Path(__file__).parent / "webui" / "index.html"

def build_app(reg, llm, cfg):
    app = FastAPI(title="Agent Hero")

    @app.get("/health")
    def health():
        return {"ok": True, "llm_reachable": llm.ping(), "tools_loaded": len(reg.all_tools())}

    @app.get("/tools")
    def tools():
        return reg.manifests

    @app.post("/agent/run")
    async def agent_run(request: Request):
        body = await request.json()
        prompt = body.get("prompt", "")
        from agenthero.agent_loop import AgentLoop
        loop = AgentLoop(llm, reg, max_iterations=cfg["agent"]["max_iterations"])
        return JSONResponse(loop.run(prompt))

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        messages = body.get("messages", [])
        tools_schema = reg.openai_tools()
        resp = llm.chat(messages, tools=tools_schema)
        # If the model called tools, run them and feed results back once.
        choice = resp.get("choices", [{}])[0]
        msg = choice.get("message", {})
        calls = msg.get("tool_calls") or []
        if calls:
            tool_msgs = [{"role": "assistant", "content": None, "tool_calls": calls}]
            for c in calls:
                fn = json.loads(c["function"]["arguments"] or "{}")
                result = reg.execute(c["function"]["name"], fn)
                tool_msgs.append({"role": "tool", "tool_call_id": c["id"}, "content": str(result)})
            followup = llm.chat(messages + tool_msgs, tools=tools_schema)
            choice2 = followup.get("choices", [{}])[0]
            return {"choices": [{"message": choice2.get("message", {})}], "agent_trace": None}
        trace = []
        return {"choices": [{"message": msg}], "agent_trace": trace}

    @app.get("/")
    def index():
        with open(WEBUI, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    return app
