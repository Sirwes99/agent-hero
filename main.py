#!/usr/bin/env python3
"""
Agent Hero - CLI entry point.

Usage:
  python main.py serve [--port 8765]     start the web host
  python main.py ask "<prompt>"          run one agent task in the terminal
  python main.py tools                   list all loaded plugins/tools
"""
import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agenthero.agent_loop import AgentLoop
from agenthero.common import load_config
from agenthero.llm_client import LLMClient
from agenthero.registry import PluginRegistry
from agenthero.server import build_app
import uvicorn

ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Agent Hero - universal local agent host")
    sub = ap.add_subparsers(dest="cmd")

    p_serve = sub.add_parser("serve", help="Start the web host (GUI + API)")
    p_serve.add_argument("--port", type=int, default=8765)

    p_ask = sub.add_parser("ask", help="Run one agent task from the terminal")
    p_ask.add_argument("prompt", help="Task for the agent")
    p_ask.add_argument("--max-iterations", type=int, default=12)

    sub.add_parser("tools", help="List loaded plugins and tools")

    args = ap.parse_args()
    cfg = load_config(ROOT / "config.json")
    reg = PluginRegistry(ROOT / "plugins")
    llm = LLMClient(cfg["llm"])

    if args.cmd == "serve":
        app = build_app(reg, llm, cfg)
        print(f"Agent Hero web host: http://127.0.0.1:{args.port}")
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.cmd == "ask":
        loop = AgentLoop(llm, reg, max_iterations=args.max_iterations)
        print(f"Task: {args.prompt}\n")
        result = loop.run(args.prompt)
        for step in result["trace"]:
            tool, a, r = step["tool"], step.get("args", {}), step.get("result", "")
            preview = (str(r) if isinstance(r, str) else json.dumps(r))[:200]
            print(f"  [{step['index']}] {tool}({json.dumps(a)}) -> {preview}")
        print(f"\nFinal answer:\n{result['answer']}")
    elif args.cmd == "tools":
        for name, manifest in reg.manifests.items():
            tools = [t["name"] for t in manifest.get("tools", [])]
            print(f"{name}: {', '.join(tools)}")


if __name__ == "__main__":
    main()
