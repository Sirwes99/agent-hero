import os
import subprocess
import sys

from agenthero.common import PROJECT_ROOT, safe_path, truncate


def handle(tool_name, args):
    if tool_name == "run_python":
        code = str(args.get("code", ""))
        if not code.strip():
            return "ERROR: 'code' is required"
        tmp_dir = os.path.join(PROJECT_ROOT, ".agenthero_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        path = os.path.join(tmp_dir, "run.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=300)
            return {"exit_code": proc.returncode, "stdout": truncate(proc.stdout), "stderr": truncate(proc.stderr, 5000)}
        except subprocess.TimeoutExpired as e:
            return {"error": "timed out", "partial_stdout": truncate(e.stdout or "", 5000)}

    if tool_name == "run_script":
        path = safe_path(args["path"])
        if not os.path.isfile(path):
            return f"ERROR: no such file: {path}"
        interpreter = args.get("interpreter")
        cmd = [interpreter, path] if interpreter else [sys.executable, path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"exit_code": proc.returncode, "stdout": truncate(proc.stdout), "stderr": truncate(proc.stderr, 5000)}
        except FileNotFoundError as e:
            return f"ERROR: interpreter not found ({e})"

    return f"ERROR: unknown tool '{tool_name}' in plugin 'coderunner'"
