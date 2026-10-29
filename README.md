# Agent Hero — a universal local agent host for Windows

Agent Hero turns any **local AI** (e.g. LM Studio's OpenAI-compatible server) into an autonomous builder: it can run shell commands, read/write files, search the web, download anything it needs, install packages, execute code, and use git — looping until the task is done.

## What you get

- **Agent loop** — the model plans, calls tools, gets results back, verifies, and iterates (up to `max_iterations` steps).
- **Plugin system** — every capability lives in `plugins/<name>/plugin.json + plugin.py`. Drop a new folder in and it's loaded automatically. No host changes needed.
- **Built-in plugins**:

| Plugin | Tools |
|---|---|
| shell | `run_command` (PowerShell/cmd) |
| files | `read_file`, `write_file`, `list_dir`, `search_files`, `grep_text`, `create_folder`, `copy_file`, `move_file`, `delete_path` |
| websearch | `web_search` (DuckDuckGo), `fetch_url` |
| downloads | `download_file`, `install_package` (pip/npm/winget), `search_packages` (PyPI/npm) |
| coderunner | `run_python`, `run_script` |
| gitops | `git` (status, log, diff, add, commit, init, branch, clone, pull, push, …) |
| envinfo | `get_environment` |

## Quick start

1. **Install Python** if you don't have it: `winget install -p Microsoft.Python.3.12` (or from python.org).
2. **Start a local LLM server.** LM Studio exposes one at `http://localhost:1234`. If your model lives elsewhere, edit `config.json`:

   ```json
   "llm": { "base_url": "http://localhost:1234", "model": "your-model-name" }
   ```

3. **Run it:**

   ```bat
   run_gui.bat        :: launches the web UI with pythonw.exe, waits for readiness, then opens it (v1.3.1)
   build_exe.bat      :: builds dist\AgentHeroHost.exe — single-file no-console launcher (double-click to run)
   ```

   or manually:

   ```bat
   python -m pip install -r requirements.txt
   python main.py serve --port 8765
   ```

4. **Use it:**
   - Open `http://127.0.0.1:8765` for the web UI (type a task, watch each tool step).
   - Or from the terminal: `python main.py ask "Build a Python CLI that converts CSV to JSON and test it"`.
   - Any OpenAI-compatible client can treat Agent Hero as a model: point it at `http://127.0.0.1:8765/v1/chat/completions` — the agent loop runs inside, and the response includes an `agent_trace` of every tool call.

## GUI

**Primary (v1.3.1): web UI.** `run_gui.bat` starts the FastAPI host with `pythonw.exe` (no console window), waits until the server is actually ready, and opens `http://127.0.0.1:8765` in your default browser. Alternatively, build once with `build_exe.bat` and double-click `dist\AgentHeroHost.exe` — a single-file no-console launcher that does the same thing without needing Python at runtime.

- **Left-side navigation:** Chat, Settings, Plugins, Folders — minimal rounded buttons; active state is a soft zinc fill, no colored borders.
- **Chat page:** task box + **Mode** dropdown (Balanced / Precise / Creative / Thinking — each sets temperature and thinking effort for the run) + indigo **Run agent** button + **Cancel**. While working, the status line ticks live (`Working… 12s · step 3`) and each tool step renders as it happens; when done you get the final answer, full trace, elapsed time, and estimated tokens/sec.
- **Settings page:** LLM endpoint/model/key/timeout, max steps, **Run limit (s)** (hard wall-clock deadline per run), mode — saved straight to `config.json` with a version stamp.
- **Plugins page:** every plugin folder listed with its tools; one tap toggles it on/off (persisted in `plugins_enabled`).
- **Folders page:** add/remove allowed roots with visible feedback, absolute-path normalization, case-insensitive dedupe, at least one root always kept.
- **Status strip** (sidebar): version, LLM reachability, model/mode, and GPU VRAM via `nvidia-smi` when available.

**Alternative: tkinter EXE.** A ready-to-run desktop app is built with PyInstaller:

```bat
dist\agent_hero\agent_hero.exe
```

- **No Python needed at runtime** — the exe bundles everything (plugins, config.json).
- Same left-side navigation and features as above, rendered in a windowed Tkinter UI instead of a browser tab.
- **Version tracking:** v1.3.1 is shown in the title/status bar; every config save stamps `version` into config.json so you can tell which app version wrote it.
- **Self-checks:** `agent_hero.exe --selftest` verifies version, config, plugins, and LLM reachability; `--smoke` additionally builds the full UI (hidden) and verifies every panel has content.

Notes:
- Config edits made in the GUI are written back to `config.json` inside `_internal/` next to the exe.
- To rebuild after adding plugins or changing code: run `build_exe.bat` from this folder (requires Python 3.x with PyInstaller).
- Optional: create a desktop shortcut pointing at `agent_hero.exe` for one-click launch.

## Useful endpoints

- `GET /health` — is the LLM reachable? how many tools loaded?
- `GET /tools` — all plugin manifests and schemas.
- `POST /v1/chat/completions` — OpenAI-compatible chat (runs the agent loop).
- `POST /agent/run` — `{ "prompt": "..." }` → final answer + trace.
- Web UI control API: `GET /api/state`, `POST /api/run` (+ `GET /api/status/{run_id}`, `POST /api/cancel/{run_id}`), `POST /api/settings`, `POST /api/folders/add|remove`, `POST /api/plugins/toggle`.

## Adding your own plugin

Create a folder, e.g. `plugins/myplugin/`:

```json
// myplugin/plugin.json
{
  "name": "myplugin",
  "description": "What it does",
  "tools": [
    {
      "name": "do_thing",
      "description": "Explain when to use it.",
      "parameters": {
        "type": "object",
        "properties": { "arg1": { "type": "string" } },
        "required": ["arg1"]
      }
    }
  ]
}
```

```python
# myplugin/plugin.py
def handle(tool_name, args):
    if tool_name == "do_thing":
        # do the work; return a string or JSON-serializable value
        return {"ok": True}
    return f"ERROR: unknown tool '{tool_name}' in plugin 'myplugin'"
```

Restart the host and it's live. Ideas: browser automation, Docker/Podman runner, database access (sqlite/psql), screenshot capture, TTS, file compression, API clients for any service you have keys for.

## Security notes

- File tools are restricted to `security.allowed_roots` in `config.json` (default: the project folder). Add more roots if needed.
- Shell commands run with your user rights — review what the agent runs; destructive file ops require explicit `force=true`.
- Downloads land in `downloads/` by default.
- There is no sandboxing of shell execution itself; treat it as a trusted assistant on your own machine.

## Requirements & limitations

- Python 3.9+ is needed to build the exe (`build_exe.bat`) and run from source; the exe itself runs standalone with no runtime dependencies.
- The local model must support **function calling** (most LM Studio models do). If the model doesn't emit tool calls, the loop simply returns its text answer.
- Web search uses DuckDuckGo's HTML endpoint — best-effort scraping; if it gets rate-limited, `fetch_url` still works for known URLs.
