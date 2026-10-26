import os
import platform
import shutil
import sys


def handle(tool_name, args):
    if tool_name != "get_environment":
        return f"ERROR: unknown tool '{tool_name}' in plugin 'envinfo'"
    try:
        free_gb = round(shutil.disk_usage(os.path.expanduser("~")).free / 1e9, 1)
    except OSError:
        free_gb = None
    return {
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "python": sys.version,
        "cwd": os.getcwd(),
        "user": os.environ.get("USERNAME", ""),
        "disk_free_gb": free_gb,
    }
