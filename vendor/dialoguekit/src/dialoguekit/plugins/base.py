from abc import ABC
from dialoguekit.plugins.hooks import Plugin

class BasePlugin(ABC, Plugin):
    """插件基类，业务插件继承此类"""
    name: str = ""

    # 可选实现：FlowProvider, ActionProvider, IntentProvider, SchemaProvider, ClarifyMessageProvider