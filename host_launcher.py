"""Agent Hero host launcher (no console window).

Starts the FastAPI web host on http://127.0.0.1:8765 in a background thread,
waits until it is ready, then opens the URL in your default browser.
Built into AgentHeroHost.exe by agent_hero_host.spec (PyInstaller, console=False).
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time

PORT = 8765
URL = "http://127.0.0.1:%d" % PORT
LOG_FILE = os.path.join(tempfile.gettempdir(), "agent_hero_host.log")


def _log(msg: str) -> None:
    """Append a timestamped line to the startup log (diagnostics without a console)."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


def _ensure_stdio() -> None:
    """A frozen console=False exe has no console, so sys.stdout/stderr are None.

    uvicorn's logging setup calls sys.stdout.isatty(), which raises AttributeError
    on None and silently kills the server thread before it can bind the port.
    Point any missing streams at NUL so startup is safe in every launch mode.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull))


def _ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=1):
            return True
    except OSError:
        return False


def main():
    _ensure_stdio()

    # In a frozen onefile exe, __file__ lives in the temp extraction dir; make sure
    # config.json exists there (the bundled copy is used when present).
    root = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(root, "config.json")
    if not os.path.exists(cfg_path):
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"llm": {"base_url": "http://localhost:1234", "model": "local-model"}, "mode": "Balanced"}, f)

    import uvicorn
    from agenthero.server import create_app

    app = create_app()
    _log("config loaded, starting uvicorn")

    def _server():
        try:
            uvicorn.run(app, host="127.0.0.1", port=PORT)
        except Exception as exc:  # pragma: no cover
            _log(f"uvicorn failed to start: {exc!r}")

    t = threading.Thread(target=_server, daemon=True)
    t.start()
    for _ in range(60):
        if _ready():
            break
        time.sleep(0.5)
    else:
        _log(f"server never became ready; uvicorn thread alive={t.is_alive()}")

    try:
        os.startfile(URL)  # opens the default browser; harmless if none is set
    except OSError:
        pass

    t.join()


if __name__ == "__main__":
    main()
