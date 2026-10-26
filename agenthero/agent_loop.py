"\"\"\"The agent loop: talk to the LLM, execute tool calls, feed results back.\"\"\"
import json

DEFAULT_SYSTEM_PROMPT = (
    \"You are an autonomous software agent running on Windows with a full toolbox:\
\"
    \"- shell: run PowerShell or cmd commands\\n\"
    \"- files: read/write/list/search/copy/move/delete files inside the workspace\\n\"
    \"- websearch: search DuckDuckGo and fetch any URL as text\\n\"
    \"- downloads: download URLs, install packages (pip/npm/winget), search package registries\\n\"
    \"- coderunner: execute Python code or scripts\\n\"
    \"- gitops: run git commands\\n\"
    \"- envinfo: inspect the environment\\n\"
    \"Work step by step: plan, act with tools, verify results, and iterate until the task is complete.\\n\"
    \"If something you need is missing (a library, a file, documentation), search online or install it first.\\n\"
    \"Create new files inside the workspace. Be concise in your final answer.\"
)


class AgentLoop:
    def __init__(self, client, registry, max_iterations=40):
        self.client = client
        self.registry = registry
        self.max_iterations = int(max_iterations)

    def run(self, messages, system_prompt=None):
        msgs = [dict(m) for m in messages]
        if not any(m.get(\"role\") == \"system\" for m in msgs):
            msgs.insert(0, {\"role\": \"system\", \"content\": system_prompt or DEFAULT_SYSTEM_PROMPT})

        tools = self.registry.tool_schemas()
        trace = []
        last_message = None

        for step in range(1, self.max_iterations + 1):
            message = self.client.chat(msgs, tools)
            last_message = message
            tool_calls = message.get(\"tool_calls\") or []
            if not tool_calls:
                return {
                    \"final_answer\": message.get(\"content\") or \"\",
                    \"steps\": step,
                    \"trace\": trace,
                }

            msgs.append(message)
            for tc in tool_calls:
                fn = tc.get(\"function\", {})
                name = fn.get(\"name\", \"\")
                raw_args = fn.get(\"arguments\", \"{}\")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                except (TypeError, ValueError):
                    args = {}
                result = self.registry.execute(name, args)
                trace.append({\"step\": step, \"tool\": name, \"args\": args, \"result\": result[:4000]})
                msgs.append({
                    \"role\": \"tool\",
                    \"tool_call_id\": tc.get(\"id\") or f\"call_{step}_{name}\",
                    \"content\": result,
                })

        return {
            \"final_answer\": (last_message or {}).get(\"content\") or \"Reached maximum iterations without a final answer.\",
            \"steps\": self.max_iterations,
            \"trace\": trace,
        }
"