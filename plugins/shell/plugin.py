import os
import subprocess

from agenthero.common import safe_path, truncate


def handle(tool_name, args):
    if tool_name != "run_command":
        return f"ERROR: unknown tool '{tool_name}' in plugin 'shell'"
    command = str(args.get("command", "")).strip()
    if not command:
        return "ERROR: 'command' is required"
    shell = args.get("shell", "powershell")
    cwd = safe_path(args["cwd"]) if args.get("cwd") else os.getcwd()
    timeout = int(args.get("timeout", 120))
    cmd = [shell, "-NoProfile", "-Command", command] if shell == "powershell" else ["cmd", "/c", command]
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": truncate(proc.stdout),
            "stderr": truncate(proc.stderr, 10000),
        }
    except subprocess.TimeoutExpired as e:
        return {"error": f"timed out after {timeout}s", "partial_stdout": truncate(e.stdout or "", 5000)}
