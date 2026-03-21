"""Plugin loader — discover, load, and manage plugins."""

from __future__ import annotations

import importlib.util
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.plugins.base import PluginBase

if TYPE_CHECKING:
    from types import ModuleType

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Metadata for a registered plugin."""

    name: str
    path: str
    module_name: str
    enabled: bool = True
    description: str = ""
    version: str = "0.0.0"
    hooks: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    config_schema: list[dict] = field(default_factory=list)


def discover_plugins(plugins_dir: str) -> list[dict]:
    """Scan *plugins_dir* for Python files and return metadata dicts.

    Each dict has keys ``name``, ``path``, and ``module``.
    Files whose names start with ``_`` are ignored.
    """
    directory = Path(plugins_dir)
    if not directory.is_dir():
        logger.debug("Plugins directory %s does not exist — nothing to discover.", plugins_dir)
        return []

    plugins: list[dict] = []
    for py_file in sorted(directory.glob("*.py")):
        plugins.append(
            {
                "name": py_file.stem,
                "path": str(py_file),
                "module": f"plugins.{py_file.stem}",
            }
        )
    return plugins


def load_plugin(plugin_info: dict) -> ModuleType:
    """Dynamically import a plugin module described by *plugin_info*.

    *plugin_info* must contain ``name``, ``path``, and ``module`` keys.
    Returns the imported module.  Raises on import failure.
    """
    spec = importlib.util.spec_from_file_location(plugin_info["module"], plugin_info["path"])
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {plugin_info['path']}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PluginRegistry:
    """Registry that tracks loaded plugins and persists state to JSON."""

    def __init__(self, plugins_dir: str) -> None:
        self.plugins_dir = plugins_dir
        self.plugins: dict[str, PluginInfo] = {}
        self._registry_path = Path(plugins_dir) / "registry.json"
        self._load_state()

    # -- public API ----------------------------------------------------------

    def register(self, name: str, module: ModuleType, enabled: bool = True) -> None:
        """Add a plugin to the registry."""
        # Extract config schema and defaults from PluginBase subclass if present.
        plugin_instance = None
        for attr_name in dir(module):
            obj = getattr(module, attr_name, None)
            if isinstance(obj, type) and obj is not PluginBase and issubclass(obj, PluginBase):
                plugin_instance = obj()
                break

        config_schema: list[dict] = []
        config: dict = {}
        description = ""
        version = "0.0.0"
        hooks: list[str] = []
        if plugin_instance is not None:
            config_schema = plugin_instance.get_config_schema()
            config = dict(plugin_instance.config)
            description = getattr(plugin_instance, "description", "")
            version = getattr(plugin_instance, "version", "0.0.0")
            # Detect which hooks the plugin overrides.
            _HOOK_NAMES = (
                "on_chunk",
                "on_ingest",
                "on_retrieve",
                "on_post_retrieve",
                "on_generate",
                "on_post_generate",
            )
            hooks = [
                h for h in _HOOK_NAMES if getattr(type(plugin_instance), h, None) is not getattr(PluginBase, h, None)
            ]

        info = PluginInfo(
            name=name,
            path=getattr(module, "__file__", "") or "",
            module_name=module.__name__,
            enabled=enabled,
            description=description,
            version=version,
            hooks=hooks,
            config=config,
            config_schema=config_schema,
        )
        # Honour previously-persisted state when re-registering.
        saved = self._saved_state.get(name)
        if saved is not None:
            info.enabled = saved.get("enabled", enabled)
            saved_config = saved.get("config")
            if saved_config and isinstance(saved_config, dict):
                info.config.update(saved_config)
        self.plugins[name] = info
        self._save_state()

    def get_enabled(self) -> list[PluginInfo]:
        """Return all enabled plugins."""
        return [p for p in self.plugins.values() if p.enabled]

    def toggle(self, name: str, enabled: bool) -> None:
        """Enable or disable a plugin by *name*."""
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        self.plugins[name].enabled = enabled
        self._save_state()

    def get_config(self, name: str) -> dict:
        """Return the current config for plugin *name*."""
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        return {
            "config": dict(self.plugins[name].config),
            "config_schema": list(self.plugins[name].config_schema),
        }

    def update_config(self, name: str, values: dict) -> dict:
        """Update config values for plugin *name*. Returns updated config."""
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        info = self.plugins[name]
        # Only accept keys that appear in the schema.
        valid_keys = {f["name"] for f in info.config_schema}
        for key, value in values.items():
            if key in valid_keys:
                info.config[key] = value
        self._save_state()
        return dict(info.config)

    # -- persistence ---------------------------------------------------------

    def _load_state(self) -> None:
        """Load previously-persisted enabled/disabled state."""
        self._saved_state: dict[str, dict] = {}
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text())
                if isinstance(data, dict):
                    self._saved_state = data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read plugin registry %s: %s", self._registry_path, exc)

    def _save_state(self) -> None:
        """Persist current plugin state to the registry JSON file."""
        data = {name: asdict(info) for name, info in self.plugins.items()}
        try:
            self._registry_path.parent.mkdir(parents=True, exist_ok=True)
            self._registry_path.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            logger.warning("Failed to write plugin registry %s: %s", self._registry_path, exc)
