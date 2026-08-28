from typing import Optional

from dialoguekit.plugins.hooks import Plugin, ClarifyMessageProvider
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.knowledge.intents import KnowledgeIntent


class PluginRegistry:
    _plugins: dict[str, Plugin] = {}

    @classmethod
    def register(cls, plugin: Plugin) -> None:
        cls._plugins[plugin.name] = plugin

    @classmethod
    def get(cls, name: str) -> Optional[Plugin]:
        return cls._plugins.get(name)

    @classmethod
    def get_all(cls) -> list[Plugin]:
        return list(cls._plugins.values())

    @classmethod
    def get_flow_files(cls) -> list[str]:
        files = []
        for plugin in cls._plugins.values():
            if hasattr(plugin, 'get_flow_files'):
                files.extend(plugin.get_flow_files())
        return files

    @classmethod
    def register_all_actions(cls, register: ActionRegister) -> None:
        for plugin in cls._plugins.values():
            if hasattr(plugin, 'register_actions'):
                plugin.register_actions(register)

    @classmethod
    def merge_intents(cls) -> dict[str, KnowledgeIntent]:
        merged = {}
        for plugin in cls._plugins.values():
            if hasattr(plugin, 'get_intents'):
                merged.update(plugin.get_intents())
        return merged

    @classmethod
    def get_clarify_provider(cls) -> Optional[ClarifyMessageProvider]:
        for plugin in cls._plugins.values():
            if hasattr(plugin, 'get_message'):
                return plugin
        return None

    @classmethod
    def discover(cls, plugin_dir: str = "plugins") -> None:
        pass


plugin_registry = PluginRegistry()