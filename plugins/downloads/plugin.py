import os
import re
import subprocess
import sys

import requests

from agenthero.common import PROJECT_ROOT, safe_path, truncate

UA = "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 Chrome/124.0"


def _default_dest(url):
    name = os.path.basename(url.split("?")[0]) or "download.bin"
    return os.path.join(PROJECT_ROOT, "downloads", name)


def handle(tool_name, args):
    if tool_name == "download_file":
        url = str(args.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            return "ERROR: url must start with http(s)://"
        dest = safe_path(args["dest"]) if args.get("dest") else _default_dest(url)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            with requests.get(url, stream=True, headers={"User-Agent": UA}, timeout=300) as r:
                r.raise_for_status()
                size = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
                        size += len(chunk)
            return {"saved": dest, "bytes": size}
        except Exception as e:
            return f"ERROR: download failed: {e}"

    if tool_name == "install_package":
        manager = args.get("manager", "pip")
        package = str(args.get("package", "")).strip()
        version = args.get("version")
        if not package:
            return "ERROR: 'package' is required"
        if manager == "pip":
            spec = f"{package}=={version}" if version else package
            cmd = [sys.executable, "-m", "pip", "install", "--quiet", spec]
        elif manager == "npm":
            spec = f"{package}@{version}" if version else package
            cmd = ["npm", "install", "--no-audit", spec]
        elif manager == "winget":
            cmd = ["winget", "install", "--exact", "--accept-sourceagreement", package]
        else:
            return f"ERROR: unsupported manager '{manager}' (use pip, npm or winget)"
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {"exit_code": proc.returncode, "stdout": truncate(proc.stdout), "stderr": truncate(proc.stderr, 5000)}
        except FileNotFoundError as e:
            return f"ERROR: command not found ({e}) — is {manager} installed?"

    if tool_name == "search_packages":
        query = str(args.get("query", "")).strip()
        registry = args.get("registry", "pypi")
        try:
            if registry == "npm":
                resp = requests.get(
                    "https://registry.npmjs.com/-/v1/search",
                    params={"text": query, "size": 10},
                    headers={"User-Agent": UA},
                    timeout=30,
                )
                data = resp.json().get("objects", [])
                lines = [f"{o['name']} v{o.get('version', '?')} — {truncate(o.get('description', ''), 200)}" for o in data]
            elif registry == "pypi":
                import html as _html

                resp = requests.get("https://pypi.org/search/", params={"q": query}, headers={"User-Agent": UA}, timeout=30)
                items = re.findall(r'<a[^>]*href="(/project/[^"]+)"[^>]*>(.*?)</a>', resp.text)
                lines = [f"{_html.unescape(t).strip()} — https://pypi.org{u}" for u, t in items[:10]]
            else:
                return f"ERROR: unsupported registry '{registry}' (use pypi or npm)"
            return "\n".join(lines) or "no results"
        except Exception as e:
            return f"ERROR: package search failed: {e}"

    return f"ERROR: unknown tool '{tool_name}' in plugin 'downloads'"
