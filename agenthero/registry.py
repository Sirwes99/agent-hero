"""Plugin registry: discovers plugins/<name>/ folders, loads their tools."""
import importlib.util
import json
import os
import sys


class PluginRegistry:
    def __init__(self, plugins_dir, enabled=None):
        """enabled: optional dict of plugin-name -> bool; missing names default to True."""
        self.plugins_dir = plugins_dir
        self.enabled = enabled
        self.plugins = {}  # tool name -> {"plugin": manifest_name, "module": module}
        self.manifests = []
        self._load()

    def _is_enabled(self, name):
        if self.enabled is None:
            return True
        return bool(self.enabled.get(name, True))

    def _load(self):
        if not os.path.isdir(self.plugins_dir):
            return
        for entry in sorted(os.listdir(self.plugins_dir)):
            d = os.path.join(self.plugins_dir, entry)
            manifest_path = os.path.join(d, "plugin.json")
            module_path = os.path.join(d, "plugin.py")
            if not (os.path.isfile(manifest_path) and os.path.isfile(module_path)):
                continue
            name = entry
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                if not self._is_enabled(manifest.get("name", name)):
                    continue
                mod_name = "agenthero_plugin_" + entry
                spec = importlib.util.spec_from_file_location(mod_name, module_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"[registry] failed to load plugin '{entry}': {e}")
                continue
            for tool in manifest.get("tools", []):
                self.plugins[tool["name"]] = {"plugin": manifest.get("name", entry), "module": module}
            self.manifests.append(manifest)

    def tool_schemas(self):
        """OpenAI-format tool schemas for all loaded plugins."""
        return [t for m in self.manifests for t in m.get("tools", [])]

    def execute(self, tool_name, args):
        info = self.plugins.get(tool_name)
        if not info:
            return f"ERROR: unknown tool '{tool_name}'"
        try:
            result = info["module"].handle(tool_name, args or {})
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result)
        except TypeError:
            return repr(result)

    def summary(self):
        lines = []
        for m in self.manifests:
            tools = ", ".join(t["name"] for t in m.get("tools", []))
            lines.append(f"- {m['name']}: {tools}")
        return "\n".join(lines)
