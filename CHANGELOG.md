# Agent Hero — Changelog

## v1.3.1 (2026-10-29)

Fix for `run_gui.bat` "Unable to connect":

1. **Launcher waits for readiness** — `run_gui.bat` no longer opens the browser after a fixed 2 s wait; it polls `netstat` until the server is actually listening (up to 60 s, covering frozen-exe extraction time), then opens `http://127.0.0.1:8765`. If the server never comes up, it prints a clear error instead of leaving a dead browser tab.
2. **New no-console host exe** — `host_launcher.py` + `agent_hero_host.spec` build `dist\AgentHeroHost.exe` (PyInstaller, single file, `console=False`): double-clicking it starts the web host in a background thread and opens the browser with zero console windows. `build_exe.bat` now builds both executables.
3. **Version tracking** — v1.3.1 stamped in the UI, server state, and config.json on every settings save.
4. **Frozen-exe bind failure root-caused & fixed** — in a `console=False` frozen exe, `sys.stdout`/`sys.stderr` are `None`; uvicorn's logging formatter calls `sys.stdout.isatty()` inside the server daemon thread and crashed silently before binding (the "Unable to connect" with no listener). `host_launcher.py` now redirects any missing stdio to `os.devnull` (`_ensure_stdio`) and logs startup failures to `%TEMP%\agent_hero_host.log`, so the exe binds in every launch mode.

## v1.3.0 (2026-10-29)

Tailwind SaaS web UI rebuild:

1. **New minimalist web UI** — the browser app at `http://127.0.0.1:8765` is rebuilt with Tailwind (vendored offline JIT compiler in `agenthero/webui/tailwind.js`): light zinc/slate monochrome, generous padding (`p-8` cards), soft rounded corners (`rounded-2xl`), subtle card shadows, Inter-first font stack, and indigo-600 used only on the primary **Run agent** button. Left-side nav (Chat / Settings / Plugins / Folders) with soft zinc active states — no colored borders.
2. **Live run feedback in the browser** — runs are background threads with a run id; the UI polls `GET /api/status/{run_id}` every 500 ms, so the status line ticks (`Working… 12s · step 3`) and each tool step renders as it happens (new `on_step` callback in `AgentLoop.run`, backward-compatible). Cancel aborts an in-flight run; a finished run always frees state for the next task.
3. **Full control API** — `GET /api/state`, `POST /api/run`, `POST /api/cancel/{run_id}`, `POST /api/settings` (persists to config.json with version stamp and rebuilds client/loop), `POST /api/folders/add|remove` (absolute-path normalization, case-insensitive dedupe, ≥1 root kept), `POST /api/plugins/toggle` (persisted in `plugins_enabled`). Legacy `/health`, `/tools`, `/v1/chat/completions`, `/agent/run` unchanged.
4. **Single source of truth for modes** — the MODES presets moved from `gui/app.py` to `agenthero/common.py`; both the web server and the tkinter GUI import them, and `/api/state` exposes the list.
5. **Launcher updated** — `run_gui.bat` now starts the FastAPI host with `pythonw.exe` (no console window) and opens `http://127.0.0.1:8765` in the default browser. The tkinter EXE remains as a bundled alternative.
6. **Version tracking** — v1.3.0 stamped in the UI, server state, and config.json on every settings save.

Fix for the post-v1.2.3 run failure:

1. **Tool payload now matches server validation** — plugin tool schemas are raw `{name, description, parameters}` entries, but LM Studio validates each `tools` item as the OpenAI envelope `{"type": "function", "function": {...}}`. `LLMClient._normalize_tools` wraps every schema into that envelope (idempotent for already-wrapped manifests), so chat requests no longer fail with HTTP 400 "invalid_literal / expected 'function'".

## v1.2.3 (2026-10-28)

Fixes for the two bugs found while testing v1.2.2:

1. **Doubled `/v1` endpoint fixed** — `LLMClient` now normalizes the configured base URL: a server root that already ends in `/v1` (e.g. `http://localhost:1235/v1`) has that suffix stripped before requests are built, so chat and health-check URLs are always exactly `{root}/v1/...`. Both bare-host (`http://host:port`) and full-`/v1` configs work; the "Unexpected endpoint or method (POST /v1/v1/chat/completions)" error is gone.
2. **New tasks always start after any run** — re-verified end-to-end that a failed run resets state (`busy=False`, status shows Done, answer box holds the ERROR text) and the next Run agent starts normally; the watchdog + per-run sequence guard remain in place so no outcome can leave the GUI stuck.

## v1.2.2 (2026-10-28)

Fixes for the two bugs found while testing v1.2.1:

1. **Status bar updates live on every run** — the 250 ms `_poll` loop is re-armed each time Run agent starts, so "Working… Ns" ticks up in real time and "Done — N step(s)" appears when a run completes (previously it stayed frozen at "Working… 0s"). The periodic health summary no longer overwrites the live run status.
2. **Input registers reliably** — the Status button's worker thread no longer calls Tk (`root.after`) from off-thread; it sets a flag that `_poll` picks up on the main thread, eliminating the Tcl event-loop desync that made clicks register only in bursts.

Fixes for the two post-test bugs in v1.2.0:

1. **"Error Choices" gone** — `llm_client.chat` no longer raises a raw `KeyError('choices')`. Malformed or unreachable server responses now raise clear diagnostics (no usable 'choices' with HTTP status, non-dict body, missing message, unreachable server), shown in the answer box as readable ERROR text.
2. **New tasks always work after any run** — the worker's `finally` guarantees `busy=False` on every outcome; a stall watchdog (run limit + 30 min margin) force-resets state with "ERROR: run stalled … State reset — you can issue a new task now." A per-run sequence guard stops a late-finishing hung worker from clobbering the live state of a newer run.
3. **Cancel actually aborts** — `AgentLoop.run` takes an optional `cancel_check`, polled before each step; cancelling ends the run with "(run cancelled)" (the in-flight step finishes first). Backward-compatible for existing callers (`main.py`, `server.py`, selftest).
4. **Thread-safe status refresh** — background workers no longer touch Tk widgets directly; widget updates hop to the main thread via `root.after(0, …)`. Defensive `_poll`/`_set_steps` so malformed results can't crash the poll chain or step rendering.

## v1.2.0 (2026-10-27)

Fixes for the five post-test issues:

1. **Folders page** — add/remove now works with visible feedback ("Added …" / "Already allowed: …" / "Removed …"), absolute-path normalization, case-insensitive dedupe, and at least one root always kept. Added a built-in read-only folder browser (pick an allowed root → Show contents lists top-level files/folders).
2. **Runs no longer stall** — each run has a hard wall-clock deadline (`agent.overall_timeout_seconds`, default 900 s, settable in Settings as "Run limit (s)"); per-step request timeouts shrink toward the deadline so a hung server can't block forever. A **Cancel** button on the Chat page aborts an in-flight run and always resets the busy state; status shows live elapsed seconds while working.
3. **No console window behind the app** — new `run_gui.bat` launches with `pythonw.exe` via `start ""`, so no black console stays open (the PyInstaller exe was already windowed).
4. **Model modes on Run agent** — Mode dropdown with presets: Balanced (temp 0.7, reasoning low), Precise (0.2, none), Creative (1.0, low), Thinking (0.4, high). Choice persists in `config.json` (`llm.mode`) and is sent as `temperature` + `reasoning_effort` with each chat (one retry without extras if the server rejects them).
5. **Server stats** — runs now report per-step usage/timing; status bar shows estimated tokens/sec from the last run, GPU VRAM via `nvidia-smi` when available, and a **Status** button that pings the LLM + refreshes GPU stats on demand (background health check every ~10 s).

## v1.1.0

- Renamed AgentForge → **Agent Hero**.
- Left-side vertical navigation with modern flat buttons; hover tooltips on all controls.
- Modern look: shadowed cards, grey edge lines between panes, dark theme.
- Version tracking: `VERSION` constant in the GUI, version stamped into config.json on every save.

## v1.0.0

- Initial Agent Hero GUI (tkinter): Chat page with agent loop + tool trace, Settings (LLM endpoint/model/key/timeout, max steps, web host start/stop), Plugins enable/disable, Folders allow-list, status bar, `--selftest` and `--smoke` headless checks.
- Plugin system: shell, files, websearch, downloads, coderunner, gitops, envinfo.
