# Agent Hero — Changelog

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
