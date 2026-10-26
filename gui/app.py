#!/usr/bin/env python3
"""
Agent Hero GUI - Tkinter desktop app.

Tabs (left sidebar): Chat, Settings, Plugins, Folders.
Version: 1.1.0
"""
import json, os, sys, threading, traceback
from pathlib import Path

VERSION = "1.1.0"
APP_NAME = "Agent Hero"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from agenthero.common import load_config, allowed_roots, safe_path
    from agenthero.llm_client import LLMClient
    from agenthero.registry import PluginRegistry
except Exception as e:
    print(f"Cannot import agent package: {e}")
    raise

import tkinter as tk
from tkinter import ttk

# ---- theme -------------------------------------------------------------
BG = "#1e1f24"
PANEL = "#262830"
CARD = "#2c2f3a"
EDGE = "#3d4150"        # grey divider lines between panes
SHADOW = "#17181d"      # fake drop shadow behind cards
FG = "#e8e9ef"
MUTED = "#9aa0b4"
ACCENT = "#6ea8ff"
OK = "#57c785"
WARN = "#f2b347"
ERR = "#e5737a"


class App:
    def __init__(self):
        self.cfg_path = ROOT / "config.json"
        self.cfg = load_config(self.cfg_path)
        self.reg = PluginRegistry(ROOT / "plugins")
        self.llm = LLMClient(self.cfg["llm"]["base_url"], self.cfg["llm"]["model"])
        self.host_state = {"running": False, "port": 8765}

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.configure(bg=BG)
        self.root.geometry("1080x720")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=PANEL)
        style.configure("TLabel", background=PANEL, foreground=FG)
        style.configure("TButton", background=CARD, foreground=FG, borderwidth=0, padding=(10, 6))
        style.configure("TEntry", fieldbackground=CARD, foreground=FG, insertbackground=ACCENT)
        style.configure("TRadiobutton", background=PANEL, foreground=FG)
        style.configure("TCheckbutton", background=PANEL, foreground=FG)
        style.configure("TNotebook.Tab", background=PANEL, foreground=FG, padding=(10, 6))

        # top bar
        top = tk.Frame(self.root, bg=PANEL, height=48)
        top.pack(side="top", fill="x")
        tk.Label(top, text=f"{APP_NAME}", font=("Segoe UI", 15, "bold"), bg=PANEL, fg=ACCENT).pack(side="left", padx=14)
        tk.Label(top, text=f"v{VERSION}", font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack(side="left")
        self.status_var = tk.StringVar(value="starting...")
        tk.Label(top, textvariable=self.status_var, font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack(side="right", padx=14)

        # grey divider under top bar
        tk.Frame(self.root, bg=EDGE, height=2).pack(side="top", fill="x")

        # left sidebar + content
        body = tk.Frame(self.root, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        self.nav = ttk.Notebook(body)
        self.nav.pack(side="left", fill="y")
        for name in ("Chat", "Settings", "Plugins", "Folders"):
            self.nav.add(name, text=name)
        # grey divider between sidebar and content
        tk.Frame(body, bg=EDGE, width=2).pack(side="left", fill="y")

        self.content = ttk.Notebook(body)
        self.content.pack(side="left", fill="both", expand=True)
        for name in ("Chat", "Settings", "Plugins", "Folders"):
            f = tk.Frame(self.content, bg=PANEL, padx=14, pady=10)
            self.content.add(name, text=name, content=f)

        # grey divider above status bar
        tk.Frame(self.root, bg=EDGE, height=2).pack(side="bottom", fill="x")
        self.statusbar = tk.Frame(self.root, bg=PANEL, height=30)
        self.statusbar.pack(side="bottom", fill="x")
        self.sb_llm = tk.Label(self.statusbar, text="LLM: checking...", font=("Segoe UI", 9), bg=PANEL, fg=MUTED)
        self.sb_llm.pack(side="left", padx=10)
        self.sb_tools = tk.Label(self.statusbar, text=f"Tools: {len(self.reg.all_tools())} loaded", font=("Segoe UI", 9), bg=PANEL, fg=MUTED)
        self.sb_tools.pack(side="left")
        self.sb_host = tk.Label(self.statusbar, text="Web host: stopped", font=("Segoe UI", 9), bg=PANEL, fg=MUTED)
        self.sb_host.pack(side="right", padx=10)

        self._build_chat()
        self._build_settings()
        self._build_plugins()
        self._build_folders()
        self._refresh_status()

    # ---- helpers ---------------------------------------------------------
    def make_card(self, parent):
        """A card with a fake drop shadow: shadow frame behind, card on top."""
        sh = tk.Frame(parent, bg=SHADOW)
        sh.pack(fill="both", expand=True, pady=(4, 0), padx=(4, 0))
        card = tk.Frame(sh, bg=CARD, bd=1, relief="raised")
        card.pack(fill="both", expand=True)
        return card

    def _tip(self, w, text):
        tip = tk.Toplevel(self.root); tip.withdraw()
        w.bind("<Enter>", lambda e: self._show_tip(w, text))
        w.bind("<Leave>", lambda e: tip.withdraw())

    def _show_tip(self, w, text):
        tip = tk.Toplevel(self.root)
        tip.overrideredirect(True)
        x, y = w.winfo_rootx() + 12, w.winfo_rooty() - 8
        tip.geometry(f"{max(160, len(text) * 9)}x34+{x}+{y}")
        lbl = tk.Label(tip, text=text, bg="#2a2c35", fg=FG, font=("Segoe UI", 9), anchor="nw")
        lbl.pack(fill="both", expand=True)

    def _refresh_status(self):
        ok = self.llm.ping()
        self.sb_llm.config(text=f"LLM: {'reachable' if ok else 'NOT reachable'}", fg=OK if ok else ERR)
        self.status_var.set(f"{APP_NAME} v{VERSION}")

    # ---- Chat tab ----------------------------------------------------------
    def _build_chat(self):
        f = self.content.nametowidget("Chat")
        card = self.make_card(f)
        tk.Label(card, text="Task for the agent", font=("Segoe UI", 10, "bold"), bg=CARD, fg=FG).pack(anchor="nw")
        self.prompt = tk.Text(card, height=5, bg=CARD, fg=FG, relief="flat", bd=0)
        self.prompt.pack(fill="x", pady=(6, 8))
        btns = tk.Frame(card, bg=CARD)
        btns.pack(anchor="nw")
        b_run = ttk.Button(btns, text="Run agent", command=self._run_agent)
        b_run.pack(side="left", padx=(0, 8))
        self._tip(b_run, "Send the task to your local LLM; tool steps appear below.")
        b_stop = ttk.Button(btns, text="Stop", command=lambda: setattr(self, "_stop", True))
        b_stop.pack(side="left")
        self._tip(b_stop, "Abort the current agent run.")

        ans_card = self.make_card(f)
        tk.Label(ans_card, text="Answer / steps", font=("Segoe UI", 10, "bold"), bg=CARD, fg=FG).pack(anchor="nw")
        self.answer = tk.Text(ans_card, height=14, bg=CARD, fg=FG, relief="flat", bd=0)
        self.answer.pack(fill="both", expand=True, pady=(6, 8))

    def _run_agent(self):
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            self.answer.delete("1.0", "end"); self.answer.insert("1.0", "(empty task)")
            return
        self._stop = False
        def worker():
            try:
                from agenthero.agent_loop import AgentLoop
                loop = AgentLoop(self.llm, self.reg, max_iterations=self.cfg["agent"]["max_iterations"])
                res = loop.run(prompt)
                lines = [f"Final answer:\n{res['answer']}", ""]
                for s in res.get("trace", []):
                    a = json.dumps(s.get("args", {}))
                    r = str(s.get("result", ""))[:300]
                    lines.append(f"[{s['index']}] {s['tool']}({a}) -> {r}")
                self.answer.delete("1.0", "end")
                self.answer.insert("1.0", "\n".join(lines))
            except Exception as e:
                self.answer.delete("1.0", "end")
                self.answer.insert("1.0", f"ERROR:\n{traceback.format_exc()}")
        threading.Thread(target=worker, daemon=True).start()

    # ---- Settings tab -------------------------------------------------------
    def _build_settings(self):
        f = self.content.nametowidget("Settings")
        card = self.make_card(f)
        rows = [
            ("LLM base URL", "llm", "base_url", "http://localhost:1234"),
            ("Model name", "llm", "model", "local-model"),
            ("Max iterations", "agent", "max_iterations", 12),
            ("Temperature", "agent", "temperature", 0.2),
        ]
        self.entries = {}
        for label, sec, key, default in rows:
            r = tk.Frame(card, bg=CARD)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=label, font=("Segoe UI", 9), bg=CARD, fg=MUTED).pack(side="left")
            e = ttk.Entry(r, width=36)
            e.insert(0, str(default))
            e.pack(side="right", fill="x")
            self.entries[key] = (sec, key, e)
            self._tip(e, f"Sets {label} in config.json.")

        btns = tk.Frame(card, bg=CARD)
        btns.pack(anchor="nw", pady=(10, 0))
        b_save = ttk.Button(btns, text="Save settings", command=self._save_settings)
        b_save.pack(side="left", padx=(0, 8))
        self._tip(b_save, "Write changes to config.json (stamps the app version).")
        b_ping = ttk.Button(btns, text="Test LLM connection", command=self._ping_llm)
        b_ping.pack(side="left")
        self._tip(b_ping, "Checks whether your local LLM server answers /v1/models.")

        host_card = self.make_card(f)
        tk.Label(host_card, text="Web host (GUI + API)", font=("Segoe UI", 10, "bold"), bg=CARD, fg=FG).pack(anchor="nw")
        hbtns = tk.Frame(host_card, bg=CARD)
        hbtns.pack(anchor="nw", pady=(6, 0))
        b_start = ttk.Button(hbtns, text="Start web host", command=lambda: self._host_toggle(True))
        b_start.pack(side="left", padx=(0, 8))
        self._tip(b_start, "Run the FastAPI server on port 8765 (web UI + API).")
        b_stop = ttk.Button(hbtns, text="Stop web host", command=lambda: self._host_toggle(False))
        b_stop.pack(side="left")
        self._tip(b_stop, "Shut the web host down.")

    def _save_settings(self):
        for key, (sec, k, e) in self.entries.items():
            v = e.get().strip()
            try:
                if k == "max_iterations":
                    self.cfg[sec][k] = int(v)
                elif k == "temperature":
                    self.cfg[sec][k] = float(v)
                else:
                    self.cfg[sec][k] = v
            except ValueError:
                pass
        self.cfg.setdefault("version", VERSION)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)
        self._refresh_status()

    def _ping_llm(self):
        ok = self.llm.ping()
        self.status_var.set("LLM reachable" if ok else "LLM NOT reachable")

    def _host_toggle(self, on: bool):
        import uvicorn
        from agenthero.server import build_app
        if on:
            app = build_app(self.reg, self.llm, self.cfg)
            t = threading.Thread(target=uvicorn.run, args=(app,), kwargs={"host": "127.0.0.1", "port": 8765}, daemon=True)
            t.start()
            self.host_state["running"] = True
        else:
            # uvicorn has no clean stop API; best effort: mark stopped.
            self.host_state["running"] = False
        self.sb_host.config(text=f"Web host: {'running on 8765' if self.host_state['running'] else 'stopped'}")

    # ---- Plugins tab --------------------------------------------------------
    def _build_plugins(self):
        f = self.content.nametowidget("Plugins")
        card = self.make_card(f)
        tk.Label(card, text="Plugins (enable/disable; saved to config.json)", font=("Segoe UI", 10, "bold"), bg=CARD, fg=FG).pack(anchor="nw")
        self.plugin_rows = {}
        for name in sorted(self.reg.manifests):
            m = self.reg.manifests[name]
            tools = [t["name"] for t in m.get("tools", [])]
            r = tk.Frame(card, bg=CARD)
            r.pack(fill="x", pady=4)
            cb = ttk.Checkbutton(r, text=name)
            enabled = self.cfg.get("plugins", {}).get(name, True)
            if enabled:
                cb.select()
            cb.pack(side="left")
            tk.Label(r, text=f"{len(tools)} tools: {', '.join(tools)}", font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(side="right")
            self.plugin_rows[name] = cb
            self._tip(cb, f"Toggle plugin '{name}'. Saved when you press Save plugins.")
        btns = tk.Frame(card, bg=CARD)
        btns.pack(anchor="nw", pady=(10, 0))
        b_save = ttk.Button(btns, text="Save plugins", command=self._save_plugins)
        b_save.pack(side="left")
        self._tip(b_save, "Persist enabled/disabled state to config.json.")

    def _save_plugins(self):
        state = {}
        for name, cb in self.plugin_rows.items():
            state[name] = bool(cb.instate())
        self.cfg.setdefault("plugins", {}).update(state)
        self.cfg.setdefault("version", VERSION)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)

    # ---- Folders tab --------------------------------------------------------
    def _build_folders(self):
        f = self.content.nametowidget("Folders")
        card = self.make_card(f)
        tk.Label(card, text="Allowed roots for file tools", font=("Segoe UI", 10, "bold"), bg=CARD, fg=FG).pack(anchor="nw")
        lb = tk.Listbox(card, height=8, bg=CARD, fg=FG, relief="flat", bd=0)
        for r in allowed_roots(self.cfg):
            lb.insert("end", str(r))
        lb.pack(fill="x", pady=(6, 8))

        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x")
        self.new_root = ttk.Entry(row, width=40)
        self.new_root.pack(side="left")
        b_add = ttk.Button(row, text="Add folder", command=self._add_folder)
        b_add.pack(side="left", padx=(8, 8))
        self._tip(b_add, "Add a folder the file tools may touch.")
        b_rm = ttk.Button(row, text="Remove selected", command=self._remove_folder)
        b_rm.pack(side="left")
        self._tip(b_rm, "Remove the highlighted folder from allowed roots.")

    def _add_folder(self):
        p = self.new_root.get().strip()
        if not p:
            return
        try:
            Path(p).resolve()
        except Exception:
            return
        roots = self.cfg.setdefault("security", {}).setdefault("allowed_roots", [])
        if str(Path(p)) not in [str(x) for x in roots]:
            roots.append(str(Path(p)))
        lb = None
        for w in self._walk(self.content.nametowidget("Folders")):
            if isinstance(w, tk.Listbox):
                lb = w; break
        if lb:
            lb.insert("end", str(Path(p)))
        self.cfg.setdefault("version", VERSION)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)

    def _remove_folder(self):
        lb = None
        for w in self._walk(self.content.nametowidget("Folders")):
            if isinstance(w, tk.Listbox):
                lb = w; break
        if not lb or not lb.selection():
            return
        sel = [lb.get(i) for i in lb.selection()]
        roots = self.cfg.setdefault("security", {}).setdefault("allowed_roots", [])
        roots[:] = [r for r in roots if str(Path(r)) not in sel]
        for i in sorted(lb.selection(), reverse=True):
            lb.delete(i)
        self.cfg.setdefault("version", VERSION)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2)

    def _walk(self, w):
        yield w
        for c in w.winfo_children():
            yield from self._walk(c)

    # ---- selftest / smoke ----------------------------------------------------
    def run_selftest(self) -> int:
        print(f"{APP_NAME} v{VERSION}")
        ok = True
        try:
            cfg = load_config(self.cfg_path)
            print("config: OK")
        except Exception as e:
            print(f"config: FAIL {e}"); ok = False
        tools = self.reg.all_tools()
        print(f"plugins: {len(self.reg.manifests)} loaded, {len(tools)} tools")
        if not tools:
            ok = False
        ping = self.llm.ping()
        print(f"llm reachable: {ping}")
        return 0 if ok else 1

    def run_smoke(self) -> int:
        # Build the full UI hidden, verify every panel has widgets.
        try:
            app = App()
            for tab in ("Chat", "Settings", "Plugins", "Folders"):
                f = app.content.nametowidget(tab)
                n = len(f.winfo_children())
                print(f"tab {tab}: {n} widgets")
                if n == 0:
                    return 1
            app.root.withdraw()
            app.root.destroy()
            return 0
        except Exception as e:
            print(f"smoke FAIL: {e}")
            return 1


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        App().run_selftest()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke":
        raise SystemExit(App().run_smoke())
    App().root.mainloop()


if __name__ == "__main__":
    main()
