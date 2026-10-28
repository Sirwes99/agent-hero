"""The agent loop: talk to the LLM, execute tool calls, feed results back."""
import json
import time

DEFAULT_SYSTEM_PROMPT = (
    "You are an autonomous software agent running on Windows with a full toolbox:\n"
    "- shell: run PowerShell or cmd commands\n"
    "- files: read/write/list/search/copy/move/delete files inside the workspace\n"
    "- websearch: search DuckDuckGo and fetch any URL as text\n"
    "- downloads: download URLs, install packages (pip/npm/winget), search package registries\n"
    "- coderunner: execute Python code or scripts\n"
    "- gitops: run git commands\n"
    "- envinfo: inspect the environment\n"
    "Work step by step: plan, act with tools, verify results, and iterate until the task is complete.\n"
    "If something you need is missing (a library, a file, documentation), search online or install it first.\n"
    "Create new files inside the workspace. Be concise in your final answer."
)


class AgentLoop:
    def __init__(self, client, registry, max_iterations=40):
        self.client = client
        self.registry = registry
        self.max_iterations = int(max_iterations)

    def run(self, messages, system_prompt=None, extra=None, overall_timeout=None):
        """Run the loop. `extra` is merged into each chat payload (mode presets).
        `overall_timeout` caps total wall time; per-step request timeouts shrink as
        the deadline approaches so a hung server can never stall the run forever."""
        msgs = [dict(m) for m in messages]
        if not any(m.get("role") == "system" for m in msgs):
            msgs.insert(0, {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT})

        tools = self.registry.tool_schemas()
        trace = []
        last_message = None
        start = time.time()
        deadline = (start + float(overall_timeout)) if overall_timeout else None
        stats = {"prompt_tokens": 0, "completion_tokens": 0, "elapsed_s": 0.0}

        for step in range(1, self.max_iterations + 1):
            remaining = (deadline - time.time()) if deadline is not None else None
            if remaining is not None and remaining <= 0:
                stats["elapsed_s"] = time.time() - start
                return {
                    "final_answer": f"Timed out after {int(overall_timeout)}s without a final answer.",
                    "steps": step - 1,
                    "trace": trace,
                    "stats": self._finalize_stats(stats),
                }

            step_timeout = int(max(5, min(self.client.timeout, remaining))) if remaining is not None else None
            message, meta = self.client.chat(msgs, tools, extra=extra, timeout=step_timeout)
            last_message = message
            usage = (meta or {}).get("usage") or {}
            stats["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
            stats["completion_tokens"] += int(usage.get("completion_tokens", 0))
            stats["elapsed_s"] += float((meta or {}).get("elapsed_s", 0.0))

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return {
                    "final_answer": message.get("content") or "",
                    "steps": step,
                    "trace": trace,
                    "stats": self._finalize_stats(stats),
                }

            msgs.append(message)
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                except (TypeError, ValueError):
                    args = {}
                result = self.registry.execute(name, args)
                trace.append({"step": step, "tool": name, "args": args, "result": result[:4000]})
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or f"call_{step}_{name}",
                    "content": result,
                })

        stats["elapsed_s"] = time.time() - start
        return {
            "final_answer": (last_message or {}).get("content") or "Reached maximum iterations without a final answer.",
            "steps": self.max_iterations,
            "trace": trace,
            "stats": self._finalize_stats(stats),
        }

    @staticmethod
    def _finalize_stats(stats):
        elapsed = max(float(stats.get("elapsed_s", 0.0)), 1e-6)
        completion = int(stats.get("completion_tokens", 0))
        return {
            "prompt_tokens": int(stats.get("prompt_tokens", 0)),
            "completion_tokens": completion,
            "total_tokens": int(stats.get("prompt_tokens", 0)) + completion,
            "elapsed_s": round(elapsed, 1),
            "tok_per_s": (completion / elapsed) if completion else None,
        }
