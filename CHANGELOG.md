# Agent Hero — Changelog

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
