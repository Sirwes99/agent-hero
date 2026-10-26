"""Agent Hero GUI \u2014 desktop control panel for the universal local agent host.

Versioned (see VERSION below). Navigation is a left-side column of modern flat
buttons: Chat / Settings / Plugins / Folders, with the content area on the right.
Every control shows a concise hover tooltip. Packages cleanly with PyInstaller
into one .exe.
"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

VERSION = "1.1.0"

def base_dir():
    """Directory holding config.json and plugins/ (the exe's data dir when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable))))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, base_dir())  # make the agenthero package importable when run from source

from agenthero.agent_loop import AgentLoop
from agenthero.llm_client import LLMClient
from agenthero.registry import PluginRegistry

BASE = base_dir()
CONFIG_PATH = os.path.join(BASE, "config.json")
PLUGINS_DIR = os.path.join(BASE, "plugins")

BG = "#1b1f2a"      # window background
PANEL = "#232938"   # sidebar / panel background
CARD = "#272e40"    # input card background
ACCENT = "#5b8cff"  # selected nav button + primary buttons
HOVER = "#2f3a56"   # nav button hover highlight
TEXT = "#e6e9f0"
MUTED = "#9aa3b8"
SHADOW = "#0c0f16"   # fake drop-shadow color (darker than BG)
EDGE = "#3d4763"     # grey outline between panes and card rings

def make_card(parent, inner_bg=CARD):
    """Wrap a widget in a fake drop-shadow card: SHADOW strip on bottom/right + 1px EDGE ring."""
    outer = tk.Frame(parent, bg=SHADOW)
    ring = tk.Frame(outer, bg=EDGE)
    body = tk.Frame(ring, bg=inner_bg)
    body.pack(in_=ring, fill="both", expand=True, padx=1, pady=1)
    ring.pack(in_=outer, fill="both", expand=True, padx=(0, 3), pady=(0, 3))
    return outer, body

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}
    llm = cfg.setdefault("llm", {})
    llm.setdefault("base_url", "http://localhost:1234")
    llm.setdefault("model", "local-model")
    llm.setdefault("api_key", "")
    llm.setdefault("timeout_seconds", 180)
    agent = cfg.setdefault("agent", {})
    agent.setdefault("max_iterations", 40)
    agent.setdefault("system_prompt", "")
    sec = cfg.setdefault("security", {})
    sec.setdefault("allowed_roots", ["."])
    sec.setdefault("shell_timeout_default", 120)
    cfg.setdefault("plugins_enabled", {})
    cfg.setdefault("version", VERSION)
    return cfg

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

class TooltipManager:
    """Hover tooltips: bound widgets show a small dark card near the cursor."""

    def __init__(self, root):
        self.root = root
        self.win = None

    def show(self, widget, text):
        if not text or self.win is not None:
            return
        x = widget.winfo_rootx() + 14
        y = widget.winfo_rooty() + 10
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        label = tk.Label(
            self.win, text=text, background="#2b3145", foreground=TEXT,
            font=("Segoe UI", 9), padx=10, pady=7, justify="left", wraplength=340,
        )
        label.pack()
        self.win.geometry(f"+{x}+{y}")

    def hide(self):
        if self.win:
            self.win.destroy()
            self.win = None

    def bind(self, widget, text):
        widget.bind("<Enter>", lambda e: self.show(widget, text))
        widget.bind("<Leave>", lambda e: self.hide())

class SideButton(tk.Button):
    """Flat modern sidebar button: hover highlight, accent color when selected."""

    def __init__(self, master, text, tip_mgr, hint, on_click):
        super().__init__(
            master, text=text, bg=PANEL, fg=TEXT, relief="flat", bd=0,
            font=("Segoe UI", 10), padx=16, pady=9,
            activebackground="#3d6fe0", activeforeground="white", command=on_click)
        self.selected = False
        tip_mgr.bind(self, hint)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        if not self.selected:
            self.configure(bg=HOVER if on else PANEL)

class App:
    def __init__(self, root):
        self.root = root
        root.title(f"Agent Hero {VERSION} \u2014 Universal Local Agent Host")
        root.geometry("1160x800")
        root.minsize(940, 660)
        root.configure(bg=BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                       bordercolor="#3d6fe0", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.configure("Ghost.TButton", background=PANEL, foreground=TEXT,
                       font=("Segoe UI", 9), padding=(10, 5))
        style.configure("Dark.TEntry", fieldbackground=CARD, foreground=TEXT,
                       insertoffset=6, padding=(7, 7))
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)
        style.configure("TSpinbox", fieldbackground=CARD, foreground=TEXT)

        self.tip = TooltipManager(root)
        self.cfg = load_config()
        self.registry = PluginRegistry(PLUGINS_DIR, enabled=self.cfg["plugins_enabled"])
        llm = self.cfg["llm"]
        self.client = LLMClient(llm.get("base_url"), llm.get("model"),
                               llm.get("api_key", ""), llm.get("timeout_seconds", 180))
        self.loop = AgentLoop(self.client, self.registry,
                             self.cfg["agent"].get("max_iterations", 40))

        self.busy = False
        self.result = None
        self.llm_ok = None
        self.web_server = None
        self.web_thread = None

        # Top bar: title + version
        top = tk.Frame(root, bg=BG)
        top.pack(side="top", fill="x")
        div_top = tk.Frame(root, bg=EDGE, height=2)
        div_top.pack(side="top")
        title = tk.Label(top, text="Agent Hero", font=("Segoe UI", 15, "bold"), fg=TEXT, bg=BG)
        ver = tk.Label(top, text=f"v{VERSION}", fg=MUTED, bg=BG, font=("Segoe UI", 9))
        self.tip.bind(title, "Agent Hero \u2014 a local AI that plans, uses tools, and builds things.")
        self.tip.bind(ver, f"App version {VERSION}.")
        title.pack(side="left", padx=(14, 8), pady=10)
        ver.pack(side="left")

        # Bottom status bar (packed before the main area so it keeps its slot)
        bar = tk.Frame(root, bg=PANEL)
        bar.pack(side="bottom", fill="x")
        div_bar = tk.Frame(root, bg=EDGE, height=2)
        div_bar.pack(side="bottom")
        self.status_lbl = tk.Label(bar, text="", fg=MUTED, bg=PANEL, font=("Segoe UI", 9), padx=12)
        self.tip.bind(self.status_lbl, "Live status: LLM reachability, loaded tools, web host state.")
        self.status_lbl.pack(side="right")

        # Main area: left sidebar navigation + content on the right
        main = tk.Frame(root, bg=BG)
        main.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(main, bg=PANEL, width=180)
        self.sidebar.pack(side="left", fill="y")
        div_side = tk.Frame(main, bg=EDGE, width=2)
        div_side.pack(side="left", fill="y")
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(side="right", fill="both", expand=True)

        nav = [
            ("Chat", "Run a task against your local model \u2014 tool steps appear below."),
            ("Settings", "LLM endpoint and model, agent limits, optional web host."),
            ("Plugins", "Enable or disable each plugin for the agent."),
            ("Folders", "Allow or deny folders the agent may read and write."),
        ]
        self.pages = {}
        for i, (name, hint) in enumerate(nav):
            btn = SideButton(self.sidebar, name, self.tip, hint, lambda n=name: self._select(n))
            page = tk.Frame(self.content, bg=BG)
            self.pages[name] = (btn, page)
            btn.pack(side="top", fill="x", pady=(16 if i == 0 else 8, 0), padx=12)

        ver_lbl = tk.Label(self.sidebar, text=f"v{VERSION}", fg=MUTED, bg=PANEL, font=("Segoe UI", 8))
        self.tip.bind(ver_lbl, f"App version {VERSION}.")
        ver_lbl.pack(side="bottom", pady=(0, 12), padx=14)

        self._build_chat()
        self._build_settings()
        self._build_plugins()
        self._build_folders()

        self._select("Chat")
        self._update_status()
        root.after(400, self._check_health)

    def _select(self, name):
        for n, (btn, page) in self.pages.items():
            sel = n == name
            btn.selected = sel
            btn.configure(bg=ACCENT if sel else PANEL, fg="white" if sel else TEXT)
            if sel:
                page.pack(fill="both", expand=True)
            else:
                page.forget()

    def _persist(self):
        """Save config, stamping it with the app version for change tracking."""
        self.cfg["version"] = VERSION
        save_config(self.cfg)

    # ------------------------------------------------------------------ Chat
    def _build_chat(self):
        page = self.pages["Chat"][1]

        head = tk.Label(page, text="Agent task", font=("Segoe UI", 12, "bold"), fg=TEXT, bg=BG)
        sub = tk.Label(page, text="Describe what to build or do \u2014 the agent plans, uses tools, and iterates until done.",
                       fg=MUTED, bg=BG, font=("Segoe UI", 9))
        head.pack(anchor="nw")
        sub.pack(anchor="nw")

        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", pady=(8, 0))
        card, body = make_card(row)
        card.pack(side="left", fill="both", expand=True)
        self.prompt = tk.Text(body, height=5, bg=CARD, fg=TEXT, relief="flat", bd=0,
                             font=("Consolas", 11), padx=9, pady=9)
        self.tip.bind(self.prompt, "Type the task here. Example: 'Build a Python CLI that converts CSV to JSON and test it'")
        self.prompt.pack(side="left", fill="both", expand=True)
        run = ttk.Button(row, text="Run agent", style="Accent.TButton", command=self._run_agent)
        self.tip.bind(run, "Send the task to your local model. Tool steps appear below.")
        run.pack(side="right")

        ans_head = tk.Label(page, text="Final answer", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG)
        ans_head.pack(anchor="nw", pady=(14, 2))
        card, body = make_card(page)
        card.pack(fill="x", pady=(0, 12))
        self.answer = tk.Text(body, height=8, bg=CARD, fg=TEXT, relief="flat", bd=0,
                             font=("Consolas", 11), padx=9, pady=9, state="disabled")
        self.tip.bind(self.answer, "The agent's final answer appears here.")
        self.answer.pack(fill="both", expand=True)

        steps_head = tk.Label(page, text="Tool steps \u2014 hover a step for details",
                             font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG)
        steps_head.pack(anchor="nw")
        card, self.steps_frame = make_card(page, inner_bg=PANEL)
        card.pack(fill="both", expand=True, pady=(4, 8))

    def _run_agent(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt or self.busy:
            return
        self.busy = True
        self.result = None
        self._set_steps([])
        self.status_lbl.configure(text="Working\u2026")

        def worker():
            try:
                self.result = self.loop.run([{"role": "user", "content": prompt}])
            except Exception as exc:
                self.result = {"final_answer": f"ERROR: {exc}", "steps": 0, "trace": []}
            self.busy = False

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(250, self._poll)

    def _poll(self):
        if not self.busy and self.result is not None:
            self.answer.configure(state="normal")
            self.answer.delete("1.0", "end")
            self.answer.insert("1.0", self.result["final_answer"])
            self.answer.configure(state="disabled")
            self._set_steps(self.result.get("trace", []))
            self.status_lbl.configure(text=f"Done \u2014 {self.result['steps']} step(s).")
            return
        self.root.after(250, self._poll)

    def _set_steps(self, trace):
        for child in self.steps_frame.winfo_children():
            child.destroy()
        for t in trace:
            card = tk.Frame(self.steps_frame, bg=CARD, relief="flat", bd=0)
            title = tk.Label(card, text=f"step {t['step']}  \u2022  {t['tool']}",
                            font=("Segoe UI", 9), fg=TEXT, bg=CARD)
            args_preview = " ".join(f"{k}={v}" for k, v in list(t.get("args", {}).items())[:4])
            detail = tk.Label(card, text=f"args: {args_preview or '{}'}",
                             font=("Segoe UI", 8), fg=MUTED, bg=CARD)
            title.pack(anchor="nw")
            detail.pack(anchor="nw")
            card.pack(fill="x", pady=2)
            hint = (f"{t['tool']} \u2014 args: {json.dumps(t.get('args', {}))}\n"
                   f"Result:\n{str(t.get('result', ''))[:1500]}")
            self.tip.bind(card, hint)

    # ------------------------------------------------------------- Settings
    def _build_settings(self):
        page = self.pages["Settings"][1]

        head = tk.Label(page, text="LLM model control", font=("Segoe UI", 12, "bold"), fg=TEXT, bg=BG)
        sub = tk.Label(page, text="Point the agent at any OpenAI-compatible local server (LM Studio, Ollama, llama.cpp\u2026).",
                       fg=MUTED, bg=BG, font=("Segoe UI", 9))
        head.pack(anchor="nw")
        sub.pack(anchor="nw")

        card, grid = make_card(page, inner_bg=PANEL)
        card.pack(fill="x", pady=(10, 4))
        self.entries = {}

        def field(row, label, value, hint):
            lab = tk.Label(grid, text=label, font=("Segoe UI", 9), fg=MUTED, bg=PANEL)
            lab.grid(row=row, column=0, sticky="w")
            widget = ttk.Entry(grid, style="Dark.TEntry")
            widget.insert(0, str(value))
            self.tip.bind(lab, hint)
            self.tip.bind(widget, hint)
            widget.grid(row=row, column=1, sticky="we", padx=(8, 0))
            return widget

        self.entries["base_url"] = field(0, "Base URL", self.cfg["llm"]["base_url"],
                                         "Server address of your local LLM, e.g. http://localhost:1234")
        self.entries["model"] = field(1, "Model name", self.cfg["llm"]["model"],
                                      "The model to use \u2014 it must support function calling.")
        self.entries["api_key"] = field(2, "API key", self.cfg["llm"].get("api_key", ""),
                                        "Optional; leave blank for local servers.")

        lab = tk.Label(grid, text="Timeout (s)", font=("Segoe UI", 9), fg=MUTED, bg=PANEL)
        lab.grid(row=3, column=0, sticky="w")
        self.entries["timeout_seconds"] = ttk.Spinbox(grid, from_=5, to=600)
        self.entries["timeout_seconds"].insert(0, str(self.cfg["llm"]["timeout_seconds"]))
        self.tip.bind(lab, "Max seconds to wait for one model response.")
        self.tip.bind(self.entries["timeout_seconds"], "Max seconds to wait for one model response.")
        self.entries["timeout_seconds"].grid(row=3, column=1, sticky="we", padx=(8, 0))

        lab = tk.Label(grid, text="Max steps", font=("Segoe UI", 9), fg=MUTED, bg=PANEL)
        lab.grid(row=4, column=0, sticky="w")
        self.entries["max_iterations"] = ttk.Spinbox(grid, from_=1, to=200)
        self.entries["max_iterations"].insert(0, str(self.cfg["agent"]["max_iterations"]))
        self.tip.bind(lab, "How many agent steps are allowed before it must answer.")
        self.tip.bind(self.entries["max_iterations"], "How many agent steps are allowed before it must answer.")
        self.entries["max_iterations"].grid(row=4, column=1, sticky="we", padx=(8, 0))

        save = ttk.Button(page, text="Save settings", style="Accent.TButton", command=self._save_settings)
        self.tip.bind(save, "Write changes to config.json and reload the agent.")
        save.pack(anchor="nw", pady=(12, 4))

        wh_head = tk.Label(page, text="Web host (optional)", font=("Segoe UI", 10, "bold"), fg=TEXT, bg=BG)
        wh_sub = tk.Label(page, text="Start the FastAPI server so you can also use Agent Hero in a browser or via its /v1/chat/completions API.",
                         fg=MUTED, bg=BG, font=("Segoe UI", 9))
        wh_head.pack(anchor="nw", pady=(16, 2))
        wh_sub.pack(anchor="nw")

        btns = tk.Frame(page, bg=BG)
        btns.pack(fill="x", pady=(8, 0))
        start = ttk.Button(btns, text="Start web host", style="Accent.TButton", command=self._start_web_host)
        stop = ttk.Button(btns, text="Stop", style="Ghost.TButton", command=self._stop_web_host)
        self.tip.bind(start, "Run the web UI + API at http://127.0.0.1:8765 in a background thread.")
        self.tip.bind(stop, "Shut down the web host if it is running.")
        start.pack(side="left")
        stop.pack(side="left", padx=(8, 0))
        self.web_lbl = tk.Label(btns, text="stopped", fg=MUTED, bg=BG, font=("Segoe UI", 9))
        self.tip.bind(self.web_lbl, "Current state of the web host.")
        self.web_lbl.pack(side="left")

    def _save_settings(self):
        llm = self.cfg["llm"]
        llm["base_url"] = self.entries["base_url"].get().strip() or "http://localhost:1234"
        llm["model"] = self.entries["model"].get().strip() or "local-model"
        llm["api_key"] = self.entries["api_key"].get().strip()
        try:
            llm["timeout_seconds"] = int(self.entries["timeout_seconds"].get())
        except (TypeError, ValueError):
            pass
        agent = self.cfg["agent"]
        try:
            agent["max_iterations"] = int(self.entries["max_iterations"].get())
        except (TypeError, ValueError):
            pass
        self._persist()
        llm_cfg = self.cfg["llm"]
        self.client = LLMClient(llm_cfg.get("base_url"), llm_cfg.get("model"),
                               llm_cfg.get("api_key", ""), llm_cfg.get("timeout_seconds", 180))
        self.registry = PluginRegistry(PLUGINS_DIR, enabled=self.cfg["plugins_enabled"])
        self.loop = AgentLoop(self.client, self.registry, agent.get("max_iterations", 40))
        self._update_status()
        self._check_health()

    def _start_web_host(self):
        if self.web_server is not None:
            return
        try:
            import uvicorn
            from agenthero.server import create_app
        except Exception as exc:
            self.web_lbl.configure(text=f"web host unavailable: {exc}")
            return
        app = create_app()
        config = uvicorn.Config(app, host="127.0.0.1", port=8765)
        self.web_server = uvicorn.Server(config)
        self.web_thread = threading.Thread(target=self.web_server.run, daemon=True)
        self.web_thread.start()
        self.web_lbl.configure(text="running at http://127.0.0.1:8765")

    def _stop_web_host(self):
        if self.web_server is not None:
            self.web_server.should_exit = True
            self.web_server = None
            self.web_thread = None
            self.web_lbl.configure(text="stopped")

    # ------------------------------------------------------------- Plugins
    def _build_plugins(self):
        page = self.pages["Plugins"][1]

        head = tk.Label(page, text="Plugin control", font=("Segoe UI", 12, "bold"), fg=TEXT, bg=BG)
        sub = tk.Label(page, text="Toggle plugins on or off \u2014 changes apply to the agent immediately.",
                       fg=MUTED, bg=BG, font=("Segoe UI", 9))
        head.pack(anchor="nw")
        sub.pack(anchor="nw")

        all_reg = PluginRegistry(PLUGINS_DIR, enabled=None)  # full list for display
        self.plugin_vars = {}
        for m in all_reg.manifests:
            name = m.get("name", "")
            card, row = make_card(page, inner_bg=PANEL)
            var = tk.BooleanVar(value=bool(self.cfg["plugins_enabled"].get(name, True)))
            cb = ttk.Checkbutton(row, text=name, variable=var)
            lab = tk.Label(row, text=m.get("description", "(no description)"),
                          fg=MUTED, bg=PANEL, font=("Segoe UI", 9), wraplength=460)
            tools_hint = "Tools: " + "; ".join(
                f"{t['name']} \u2014 {t['description']}" for t in m.get("tools", []))
            self.tip.bind(lab, tools_hint)
            self.tip.bind(cb, f"Enable or disable the {name} plugin for the agent.")
            cb.pack(side="left")
            lab.pack(side="left", fill="x", expand=True, padx=(12, 8))
            var.trace_add("write", lambda *a: self._toggle_plugin(name, bool(var.get())))
            card.pack(fill="x", pady=3)

    def _toggle_plugin(self, name, enabled):
        self.cfg["plugins_enabled"][name] = enabled
        self._persist()
        self.registry = PluginRegistry(PLUGINS_DIR, enabled=self.cfg["plugins_enabled"])
        self.loop = AgentLoop(self.client, self.registry,
                             self.cfg["agent"].get("max_iterations", 40))
        self._update_status()

    # ------------------------------------------------------------- Folders
    def _build_folders(self):
        page = self.pages["Folders"][1]

        head = tk.Label(page, text="Folder sandbox", font=("Segoe UI", 12, "bold"), fg=TEXT, bg=BG)
        sub = tk.Label(page, text="The agent can only read/write inside these folders. Add or remove them here.",
                       fg=MUTED, bg=BG, font=("Segoe UI", 9))
        head.pack(anchor="nw")
        sub.pack(anchor="nw")

        add = ttk.Button(page, text="Add folder\u2026", style="Accent.TButton", command=self._add_folder)
        self.tip.bind(add, "Pick a folder to allow the agent to read and write.")
        add.pack(anchor="nw", pady=(10, 8))

        card, self.roots_frame = make_card(page, inner_bg=PANEL)
        card.pack(fill="both", expand=True, pady=(0, 8))
        self._render_roots()

    def _abs_roots(self):
        return [os.path.abspath(os.path.expanduser(r)) for r in self.cfg["security"]["allowed_roots"]]

    def _render_roots(self):
        for child in self.roots_frame.winfo_children():
            child.destroy()
        for path in self._abs_roots():
            card, row = make_card(self.roots_frame, inner_bg=CARD)
            lab = tk.Label(row, text=path, font=("Segoe UI", 9), fg=TEXT, bg=CARD)
            rem = ttk.Button(row, text="Remove", style="Ghost.TButton",
                           command=lambda p=path: self._remove_root(p))
            self.tip.bind(lab, "The agent can read and write inside this folder.")
            self.tip.bind(rem, "Stop allowing the agent to touch this folder.")
            lab.pack(side="left")
            rem.pack(side="right", padx=(0, 8))
            card.pack(fill="x", pady=2)

    def _add_folder(self):
        chosen = filedialog.askdirectory(title="Choose a folder to allow the agent to use")
        if not chosen:
            return
        ap = os.path.abspath(chosen)
        roots = self.cfg["security"]["allowed_roots"]
        if ap not in self._abs_roots():
            roots.append(ap)
            self._persist()
        self._render_roots()

    def _remove_root(self, path):
        abs_roots = self._abs_roots()
        keep = [r for r in self.cfg["security"]["allowed_roots"]
               if os.path.abspath(os.path.expanduser(r)) != path]
        if not keep:
            keep = ["."]
        self.cfg["security"]["allowed_roots"] = keep
        self._persist()
        self._render_roots()

    # --------------------------------------------------------------- Status
    def _update_status(self):
        ok_txt = "reachable" if self.llm_ok else ("unreachable" if self.llm_ok is False else "checking\u2026")
        web_txt = "running at http://127.0.0.1:8765" if self.web_server else "stopped"
        self.status_lbl.configure(
            text=f"v{VERSION}  \u2022  {self.client.base_url} \u2022 {ok_txt}  |  {len(self.registry.plugins)} tools loaded  |  web host: {web_txt}")

    def _check_health(self):
        def worker():
            self.llm_ok = self.client.ping()
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(2500, lambda: self._update_status())

def selftest():
    """Headless check: prints version, resolved paths, loaded plugins, and LLM reachability."""
    print(f"version: {VERSION}")
    print(f"base_dir: {BASE}")
    print(f"config.json: {CONFIG_PATH} (exists={os.path.exists(CONFIG_PATH)})")
    reg = PluginRegistry(PLUGINS_DIR, enabled=None)
    names = [m.get("name") for m in reg.manifests]
    print(f"plugins found: {names} ({len(reg.plugins)} tools)")
    llm = load_config()["llm"]
    client = LLMClient(llm.get("base_url"), llm.get("model"),
                       llm.get("api_key", ""), llm.get("timeout_seconds", 180))
    print(f"LLM ping {client.base_url}: {client.ping()}")

def smoke():
    """Headless UI check: builds the full GUI (hidden) and verifies every page has content."""
    root = tk.Tk()
    root.withdraw()
    app = App(root)
    ok = True
    for name, (btn, page) in app.pages.items():
        n = len(page.winfo_children())
        print(f"page {name}: {n} widgets")
        if n == 0:
            ok = False
    print("status bar:", repr(app.status_lbl.cget("text")))
    root.destroy()
    return 0 if ok else 1

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        selftest()
    elif "--smoke" in sys.argv[1:]:
        raise SystemExit(smoke())
    else:
        main()
