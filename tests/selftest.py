"""Offline self-test: verifies plugin loading and the agent loop plumbing without an LLM.

Run:  python tests/selftest.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root

from agenthero.agent_loop import AgentLoop
from agenthero.registry import PluginRegistry


class ScriptedClient:
    """Stands in for LLMClient: replays a scripted sequence of tool calls."""

    def __init__(self, script):
        self.script = list(script)
        self.i = 0

    def chat(self, messages, tools=None):
        step = self.script[self.i]
        self.i += 1
        if "tool_calls" in step:
            return {"role": "assistant", "content": step.get("content"), "tool_calls": step["tool_calls"]}
        return {"role": "assistant", "content": step["final"]}


def main():
    registry = PluginRegistry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins"))
    print(f"loaded {len(registry.plugins)} tools from {len(registry.manifests)} plugins")

    script = [
        {"tool_calls": [{"id": "c1", "function": {"name": "get_environment", "arguments": "{}"}}]},
        {"tool_calls": [{"id": "c2", "function": {
            "name": "write_file",
            "arguments": json.dumps({"path": "selftest/hello.txt", "content": "hello agent hero"})}}]},
        {"tool_calls": [{"id": "c3", "function": {
            "name": "read_file",
            "arguments": json.dumps({"path": "selftest/hello.txt"})}}]},
        {"final": "Done: wrote and read selftest/hello.txt."},
    ]

    loop = AgentLoop(ScriptedClient(script), registry)
    result = loop.run([{"role": "user", "content": "run the self test"}])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
