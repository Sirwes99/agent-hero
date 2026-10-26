"""Shared helpers for the host and all plugins."""
import json
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    path = os.path.join(PROJECT_ROOT, "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
