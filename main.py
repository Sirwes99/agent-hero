"""Agent Hero entry point: serve the host or run one-shot agent tasks from the CLI."""
import argparse
import os

from agenthero.agent_loop import AgentLoop
from agenthero.common import load_config
from agenthero.llm_client import LLMClient
from agenthero.registry import PluginRegistry


def build_components():
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    client = LLMClient(
        base_url=llm_cfg.get("base_url", "http://localhost:1234"),
        model=llm_cfg.get("model", "local-model"),
        api_key=llm_cfg.get("api_key", ""),
        timeout=llm_cfg.get("timeout_seconds", 180),
    )
    registry = PluginRegistry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins"))
    loop = AgentLoop(client, registry, cfg.get("agent", {}).get("max_iterations", 40))
    return client, registry, loop


def cmd_serve(args):
    import uvicorn

    from agenthero.server import create_app

    app = create_app()
    print(f"Agent Hero host starting on http://{args.host}:{args.port}")
    print("Open the web UI at that URL, or point any OpenAI-compatible client")
    print("at /v1/chat/completions (e.g. LM Studio's local server).")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_ask(args):
    client, registry, loop = build_components()
    if not client.ping():
        print(f"WARNING: LLM server not reachable at {client.base_url} (is LM Studio running?)")
    result = loop.run([{"role": "user", "content": args.prompt}], system_prompt=args.system)
    for t in result["trace"]:
        preview_args = str(t["args"])[:120]
        print(f"[step {t['step']}] {t['tool']}({preview_args})")
        print("  -> " + t["result"][:300].replace("\n", "\n     "))
    print("\n--- FINAL ANSWER ---")
    print(result["final_answer"])


def cmd_tools(args):
    _, registry, _ = build_components()
    for m in registry.manifests:
        print(f"\n{m['name']} — {m.get('description', '')}")
        for t in m.get("tools", []):
            print(f"  • {t['name']}: {t['description']}")


def main():
    parser = argparse.ArgumentParser(prog="agent_hero", description="Universal local agent host with pluggable tools.")
    sub = parser.add_subparsers(dest="command")

    p_serve = sub.add_parser("serve", help="Run the HTTP host (web UI + OpenAI-compatible API)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)

    p_ask = sub.add_parser("ask", help="Run one agent task from the terminal")
    p_ask.add_argument("prompt", help="Task for the agent")
    p_ask.add_argument("--system", default=None, help="Optional custom system prompt")

    sub.add_parser("tools", help="List all loaded plugin tools")

    args = parser.parse_args()
    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "tools":
        cmd_tools(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
