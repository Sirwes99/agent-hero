import os
import subprocess

from agenthero.common import safe_path, truncate

ALLOWED = {
    "status", "log", "diff", "add", "commit", "init", "branch", "clone",
    "pull", "push", "fetch", "tag", "remote", "checkout", "describe",
}


def handle(tool_name, args):
    if tool_name != "git":
        return f"ERROR: unknown tool '{tool_name}' in plugin 'gitops'"
    command = str(args.get("command", "")).strip()
    parts = command.split()
    if not parts or parts[0] not in ALLOWED:
        allowed = ", ".join(sorted(ALLOWED))
        return f"ERROR: git subcommand must be one of: {allowed}"
    cwd = safe_path(args["cwd"]) if args.get("cwd") else os.getcwd()
    try:
        proc = subprocess.run(["git"] + parts, cwd=cwd, capture_output=True, text=True, timeout=300)
        return {"exit_code": proc.returncode, "stdout": truncate(proc.stdout), "stderr": truncate(proc.stderr, 5000)}
    except FileNotFoundError:
        return "ERROR: git is not installed"
