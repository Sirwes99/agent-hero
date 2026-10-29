"""Shared helpers for the host and all plugins."""
import json
import os
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick model-mode presets: temperature + reasoning_effort sent with each chat.
MODES = {
    "Balanced": {"temperature": 0.7, "reasoning_effort": "low"},
    "Precise": {"temperature": 0.2, "reasoning_effort": "none"},
    "Creative": {"temperature": 1.0, "reasoning_effort": "low"},
    "Thinking": {"temperature": 0.4, "reasoning_effort": "high"},
}


def load_config():
    path = os.path.join(PROJECT_ROOT, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg, path=None):
    """Write config to disk (defaults to the project's config.json)."""
    with open(path or os.path.join(PROJECT_ROOT, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def allowed_roots(cfg=None):
    """Absolute paths the agent is allowed to touch."""
    cfg = cfg or load_config()
    roots = []
    for r in cfg.get("security", {}).get("allowed_roots", ["."]):
        ap = os.path.abspath(os.path.expanduser(r))
        if ap not in roots:
            roots.append(ap)
    return roots


def safe_path(p, cfg=None):
    """Resolve a path and ensure it is inside one of the allowed roots."""
    ap = os.path.abspath(os.path.expanduser(str(p)))
    for root in allowed_roots(cfg):
        if ap == root or ap.startswith(root + os.sep):
            return ap
    raise PermissionError(f"Path is outside allowed roots: {ap}")


def truncate(text, limit=20000):
    text = str(text)
    if len(text) > limit:
        return text[:limit] + f"\n...[truncated; {len(text)} chars total]"
    return text


def gpu_stats():
    """VRAM usage per GPU via nvidia-smi, or None when unavailable.

    Returns a list of {name, used_mib, total_mib, util_pct} dicts.
    """
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            try:
                out.append({
                    "name": parts[0],
                    "used_mib": int(float(parts[1])),
                    "total_mib": int(float(parts[2])),
                    "util_pct": float(parts[3]),
                })
            except ValueError:
                pass
    return out or None
