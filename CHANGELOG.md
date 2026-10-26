# Changelog — Agent Hero

## v1.1.0
- Visual depth pass: fake drop-shadow cards on every content box, and grey 2px divider lines between the top bar, sidebar, content area, and status bar.
- gui/app.py restored in the repo (fixed corrupted blob).

## v1.0.0
- Initial build of Agent Hero (renamed from AgentForge): universal local agent host with a Tkinter GUI — left-side navigation buttons (Chat / Settings / Plugins / Folders), hover tooltips, LLM model control, plugin toggles, folder sandboxing, live status bar, and version stamping in config.json.
- 7 plugins: coderunner, downloads, envinfo, files, gitops, shell, websearch — the agent can run code, download anything, inspect its environment, read/write files, use Git, run shell commands, search the web, and fetch any URL.