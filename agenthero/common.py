"""Shared helpers: config, allowed roots, safe path handling."""
import json
from pathlib import Path

def load_config(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "llm": {"base_url": "http://localhost:1234", "model": "local-model"},
            "agent": {"max_iterations": 12, "temperature": 0.2},
            "security": {"allowed_roots": [str(Path.cwd())]},
        }


def allowed_roots(cfg: dict) -> list[Path]:
    return [Path(r) for r in cfg.get("security", {}).get("allowed_roots", [])]


def safe_path(p: str, roots: list[Path]) -> Path | None:
    """Resolve p; return it only if it is inside one of the allowed roots."""
    try:
        cand = (Path(roots[0]) / p).resolve() if not Path(p).is_absolute() else Path(p)
    except Exception:
        return None
    for root in roots:
        try:
            cand.relative_to(root.resolve())
            return cand
        except ValueError:
            continue
    return None
