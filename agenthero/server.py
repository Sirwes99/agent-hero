"""FastAPI host: minimalist web UI + agent control API + OpenAI-compatible endpoint."""
import json
import os
import threading
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .agent_loop import AgentLoop
from .common import MODES, gpu_stats, load_config, save_config
from .llm_client import LLMClient
from .registry import PluginRegistry

VERSION = "1.3.1"


def create_app():
    cfg = load_config()
    lock = threading.Lock()            # guards config rebuilds

    runs = {}                        # run_id -> live run record
    runs_lock = threading.Lock()     # guards the runs dict

    app = FastAPI(title="Agent Hero — universal local agent host")

    def _build_state(cfg):
        llm_cfg = cfg.get("llm", {})
        client = LLMClient(
            base_url=llm_cfg.get("base_url", "http://localhost:1234"),
            model=llm_cfg.get("model", "local-model"),
            api_key=llm_cfg.get("api_key", ""),
            timeout=llm_cfg.get("timeout_seconds", 180),
        )
        registry = PluginRegistry(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins"),
            enabled=cfg.get("plugins_enabled"),
        )
        loop = AgentLoop(client, registry, int(cfg.get("agent", {}).get("max_iterations", 40)))
        return {"cfg": cfg, "client": client, "registry": registry, "loop": loop}

    state = _build_state(cfg)         # {"cfg", "client", "registry", "loop"}

    def _plugin_list(cfg):
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins")
        if not os.path.isdir(plugins_dir):
            return []
        enabled_map = cfg.get("plugins_enabled", {})
        out = []
        for entry in sorted(os.listdir(plugins_dir)):
            d = os.path.join(plugins_dir, entry)
            manifest_path = os.path.join(d, "plugin.json")
            if not (os.path.isdir(d) and os.path.isfile(manifest_path)):
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    m = json.load(f)
            except Exception:
                continue
            name = m.get("name", entry)
            out.append({
                "name": name,
                "description": m.get("description", ""),
                "tools": [t["name"] for t in m.get("tools", [])],
                "enabled": bool(enabled_map.get(name, True)),
            })
        return out

    def _state_payload():
        with lock:
            cfg, client = state["cfg"], state["client"]
        vram = gpu_stats()
        return {
            "version": VERSION,
            "modes": list(MODES),
            "llm": {
                "base_url": client.base_url,
                "model": client.model,
                "mode": cfg.get("llm", {}).get("mode", "Balanced"),
            },
            "agent": {
                "max_iterations": int(cfg.get("agent", {}).get("max_iterations", 40)),
                "overall_timeout_seconds": int(cfg.get("agent", {}).get("overall_timeout_seconds", 900)),
            },
            "folders": [os.path.abspath(os.path.expanduser(r)) for r in cfg.get("security", {}).get("allowed_roots", [])],
            "plugins": _plugin_list(cfg),
            "health": {"llm_reachable": client.ping(), "vram": vram},
        }

    # ------------------------------------------------------------- static UI
    @app.get("/")
    def index():
        return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui", "index.html"))

    @app.get("/tailwind.js")
    def tailwind_js():
        return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui", "tailwind.js"))

    # ------------------------------------------------------------- control API
    @app.get("/api/state")
    def api_state():
        return _state_payload()

    @app.post("/api/run")
    async def api_run(request: Request):
        body = await request.json()
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            return JSONResponse({"error": "prompt is required"}, status_code=400)
        mode = body.get("mode", state["cfg"].get("llm", {}).get("mode", "Balanced"))
        if mode not in MODES:
            return JSONResponse({"error": f"unknown mode '{mode}' (use one of {', '.join(MODES)})"}, status_code=400)

        with lock:
            loop, cfg = state["loop"], state["cfg"]

        run_id = uuid.uuid4().hex[:12]
        rec = {"busy": True, "started": time.time(), "steps_done": 0, "cancel": False, "result": None}
        with runs_lock:
            runs[run_id] = rec

        def on_step(step, tool_name, args, result):
            with runs_lock:
                if run_id in runs:
                    runs[run_id]["steps_done"] = step

        def worker():
            try:
                res = loop.run(
                    [{"role": "user", "content": prompt}],
                    extra=MODES.get(mode),
                    overall_timeout=float(cfg.get("agent", {}).get("overall_timeout_seconds", 900)),
                    cancel_check=lambda: rec["cancel"],
                    on_step=on_step,
                )
            except Exception as exc:
                res = {"final_answer": f"ERROR: {exc}", "steps": 0, "trace": [], "stats": None}
            with runs_lock:
                if run_id in runs and rec["busy"]:
                    rec["busy"] = False
                    rec["result"] = res

        threading.Thread(target=worker, daemon=True).start()
        return {"run_id": run_id}

    @app.get("/api/status/{run_id}")
    def api_status(run_id):
        with runs_lock:
            rec = runs.get(run_id)
            if not rec:
                return JSONResponse({"error": "unknown run"}, status_code=404)
            payload = {
                "busy": rec["busy"],
                "elapsed_s": round(time.time() - rec["started"], 1),
                "steps_done": rec["steps_done"],
            }
            if not rec["busy"] and rec["result"]:
                payload.update(rec["result"])
        return payload

    @app.post("/api/cancel/{run_id}")
    def api_cancel(run_id):
        with runs_lock:
            rec = runs.get(run_id)
            if not rec or not rec["busy"]:
                return JSONResponse({"error": "no active run to cancel"}, status_code=404)
            rec["cancel"] = True
        return {"ok": True}

    @app.post("/api/settings")
    async def api_settings(request: Request):
        body = await request.json()
        with lock:
            cfg = state["cfg"]
            llm_cfg, agent_cfg = cfg.setdefault("llm", {}), cfg.setdefault("agent", {})

        for key in ("base_url", "model", "api_key"):
            if key in body and isinstance(body[key], str):
                llm_cfg[key] = body[key].strip()
        try:
            if "timeout_seconds" in body:
                llm_cfg["timeout_seconds"] = int(float(body["timeout_seconds"]))
            if "max_iterations" in body:
                agent_cfg["max_iterations"] = int(float(body["max_iterations"]))
            if "overall_timeout_seconds" in body:
                agent_cfg["overall_timeout_seconds"] = int(float(body["overall_timeout_seconds"]))
        except (TypeError, ValueError):
            return JSONResponse({"error": "numeric fields must be numbers"}, status_code=400)

        mode = body.get("mode")
        if mode is not None:
            if mode not in MODES:
                return JSONResponse({"error": f"unknown mode '{mode}' (use one of {', '.join(MODES)})"}, status_code=400)
            llm_cfg["mode"] = mode

        cfg["version"] = VERSION
        save_config(cfg)
        with lock:
            state.update(_build_state(cfg))
        return _state_payload()

    @app.post("/api/folders/add")
    async def api_folders_add(request: Request):
        body = await request.json()
        p = (body.get("path") or "").strip()
        if not p:
            return JSONResponse({"error": "path is required"}, status_code=400)
        ap = os.path.abspath(os.path.expanduser(p))
        with lock:
            cfg = state["cfg"]
            roots = [os.path.abspath(os.path.expanduser(r)) for r in cfg.get("security", {}).get("allowed_roots", [])]
            if any(ap.lower() == r.lower() for r in roots):
                return {"message": f"Already allowed: {ap}", "folders": roots}
            roots.append(ap)
            cfg.setdefault("security", {})["allowed_roots"] = roots
            save_config(cfg)
        return {"message": f"Added folder: {ap}", "folders": roots}

    @app.post("/api/folders/remove")
    async def api_folders_remove(request: Request):
        body = await request.json()
        p = (body.get("path") or "").strip()
        if not p:
            return JSONResponse({"error": "path is required"}, status_code=400)
        ap = os.path.abspath(os.path.expanduser(p))
        with lock:
            cfg = state["cfg"]
            roots = [os.path.abspath(os.path.expanduser(r)) for r in cfg.get("security", {}).get("allowed_roots", [])]
            idx = next((i for i, r in enumerate(roots) if r.lower() == ap.lower()), None)
            if idx is None:
                return {"message": f"Not in the allowed list: {ap}", "folders": roots}
            if len(roots) == 1:
                return {"message": "At least one allowed folder must remain.", "folders": roots}
            del roots[idx]
            cfg.setdefault("security", {})["allowed_roots"] = roots
            save_config(cfg)
        return {"message": f"Removed folder: {ap}", "folders": roots}

    @app.post("/api/plugins/toggle")
    async def api_plugins_toggle(request: Request):
        body = await request.json()
        name = (body.get("name") or "").strip()
        enabled = bool(body.get("enabled", True))
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins")
        known = [d for d in sorted(os.listdir(plugins_dir)) if os.path.isdir(os.path.join(plugins_dir, d))] \
            if os.path.isdir(plugins_dir) else []
        if name not in known:
            return JSONResponse({"error": f"unknown plugin '{name}'"}, status_code=404)
        with lock:
            cfg = state["cfg"]
            cfg.setdefault("plugins_enabled", {})[name] = enabled
            save_config(cfg)
            state.update(_build_state(cfg))
        return _state_payload()

    # ------------------------------------------------------------- legacy API
    @app.get("/health")
    def health():
        with lock:
            client, reg = state["client"], state["registry"]
        return {
            "status": "ok",
            "version": VERSION,
            "llm_base_url": client.base_url,
            "model": client.model,
            "llm_reachable": client.ping(),
            "tools_loaded": len(reg.plugins),
        }

    @app.get("/tools")
    def tools():
        with lock:
            reg = state["registry"]
        return {"plugins": reg.manifests, "tool_count": len(reg.plugins)}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        """OpenAI-compatible endpoint. Runs the full agent loop and returns the final answer."""
        body = await request.json()
        messages = body.get("messages", [])
        if not messages:
            return JSONResponse({"error": "no messages provided"}, status_code=400)
        with lock:
            client, loop = state["client"], state["loop"]
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
        with lock:
            loop = state["loop"]
        result = loop.run([{"role": "user", "content": prompt}])
        return {"final_answer": result["final_answer"], "steps": result["steps"], "trace": result["trace"]}

    return app
