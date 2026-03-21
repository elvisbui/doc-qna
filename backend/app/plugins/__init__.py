"""Plugin system for doc-qna."""

from app.plugins.base import PluginBase
from app.plugins.loader import PluginRegistry, discover_plugins, load_plugin

__all__ = ["PluginBase", "PluginRegistry", "discover_plugins", "load_plugin"]
