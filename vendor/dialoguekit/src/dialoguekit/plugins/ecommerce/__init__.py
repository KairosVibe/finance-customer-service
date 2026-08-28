import os
from typing import list, dict
from dialoguekit.plugins.base import BasePlugin
from dialoguekit.plugins.hooks import FlowProvider, ActionProvider, IntentProvider, SchemaProvider, ClarifyMessageProvider
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.knowledge.intents import KnowledgeIntent
from dialoguekit.domain.state import DialogueState
from dialoguekit.plan.turn_plan import ClarifyReason


class EcommercePlugin(BasePlugin, FlowProvider, ActionProvider, IntentProvider, SchemaProvider, ClarifyMessageProvider):
    name = "ecommerce"

    def get_flow_files(self) -> list[str]:
        base = os.path.dirname(__file__)
        return [
            os.path.join(base, "flows", "system_flows.yml"),
            os.path.join(base, "flows", "user_flows.yml"),
        ]

    def register_actions(self, register: ActionRegister) -> None:
        from .actions.lookup_order_status import ActionLookupOrderStatus
        from .actions.lookup_logistics import ActionLookupLogistics
        from .actions.recommend_similar_products import ActionRecommendSimilarProducts
        register.registry_action(ActionLookupOrderStatus())
        register.registry_action(ActionLookupLogistics())
        register.registry_action(ActionRecommendSimilarProducts())

    def get_intents(self) -> dict[str, KnowledgeIntent]:
        from .intents import KNOWLEDGE_INTENTS
        return KNOWLEDGE_INTENTS

    def get_object_types(self) -> list[str]:
        return ["order", "product"]

    def get_message(self, reason: ClarifyReason, state: DialogueState) -> str:
        from .clarify import build_clarify_message
        return build_clarify_message(reason, state)


from dialoguekit.plugins.registry import plugin_registry
plugin_registry.register(EcommercePlugin())