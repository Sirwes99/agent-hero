import fnmatch
import os
import shutil

from agenthero.common import safe_path, truncate


def _glob_match(rel_name, pattern):
    return (
        fnmatch.fnmatch(rel_name.lower(), pattern.lower())
        or fnmatch.fnmatch(os.path.basename(rel_name).lower(), pattern.lower())
    )


def handle(tool_name, args):
    if tool_name == "read_file":
        p = safe_path(args["path"])
        if not os.path.isfile(p):
            return f"ERROR: no such file: {p}"
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return truncate(f.read(), int(args.get("max_chars", 20000)))

    if tool_name == "write_file":
        p = safe_path(args["path"])
        content = args.get("content", "")
        parent = os.path.dirname(p) or "."
        os.makedirs(parent, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return {"written": p, "bytes": len(content.encode("utf-8"))}

    if tool_name == "list_dir":
        p = safe_path(args.get("path", "."))
        if not os.path.isdir(p):
            return f"ERROR: no such directory: {p}"
        entries = []
        for name in sorted(os.listdir(p)):
            full = os.path.join(p, name)
            kind = "dir " if os.path.isdir(full) else "file"
            size = "" if kind == "dir " else f" ({os.path.getsize(full)})"
            entries.append(f"{kind} {name}{size}")
        return truncate("\n".join(entries))

    if tool_name == "search_files":
        p = safe_path(args.get("path", "."))
        pattern = args["pattern"]
        max_results = int(args.get("max_results", 100))
        matches = []
        for root, _, files in os.walk(p):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), p)
                if _glob_match(rel, pattern):
                    matches.append(rel)
                    if len(matches) >= max_results:
                        return truncate("\n".join(matches))
        return "\n".join(matches) or "no matches"

    if tool_name == "grep_text":
        p = safe_path(args.get("path", "."))
        pattern = str(args.get("pattern", "")).lower()
        max_matches = int(args.get("max_matches", 50))
        if not pattern:
            return "ERROR: 'pattern' is required"
        matches = []
        for root, _, files in os.walk(p):
            for name in files:
                full = os.path.join(root, name)
                try:
                    if os.path.getsize(full) > 2_000_000:
                        continue
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if pattern in line.lower():
                                matches.append(f"{os.path.relpath(full, p)}:{i}: {line.strip()[:200]}")
                                if len(matches) >= max_matches:
                                    return truncate("\n".join(matches))
                except OSError:
                    continue
        return "\n".join(matches) or "no matches"

    if tool_name == "create_folder":
        p = safe_path(args["path"])
        os.makedirs(p, exist_ok=True)
        return {"created": p}

    if tool_name == "copy_file":
        src, dst = safe_path(args["src"]), safe_path(args["dst"])
        if not os.path.exists(src):
            return f"ERROR: no such path: {src}"
        shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
        return {"copied_to": dst}

    if tool_name == "move_file":
        src, dst = safe_path(args["src"]), safe_path(args["dst"])
        if not os.path.exists(src):
            return f"ERROR: no such path: {src}"
        parent = os.path.dirname(dst) or "."
        os.makedirs(parent, exist_ok=True)
        shutil.move(src, dst)
        return {"moved_to": dst}

    if tool_name == "delete_path":
        p = safe_path(args["path"])
        if not args.get("force"):
            return "ERROR: deletion requires force=true to confirm"
        if not os.path.exists(p):
            return f"no such path: {p}"
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        return {"deleted": p}

    return f"ERROR: unknown tool '{tool_name}' in plugin 'files'"
