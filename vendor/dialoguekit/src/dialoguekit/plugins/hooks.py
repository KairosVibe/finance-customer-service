from typing import Protocol, runtime_checkable
from dialoguekit.domain.state import DialogueState
from dialoguekit.plan.turn_plan import ClarifyReason
from dialoguekit.knowledge.intents import KnowledgeIntent
from dialoguekit.task.action.register import ActionRegister

@runtime_checkable
class FlowProvider(Protocol):
    def get_flow_files(self) -> list[str]: ...

@runtime_checkable
class ActionProvider(Protocol):
    def register_actions(self, register: ActionRegister) -> None: ...

@runtime_checkable
class IntentProvider(Protocol):
    def get_intents(self) -> dict[str, KnowledgeIntent]: ...

@runtime_checkable
class SchemaProvider(Protocol):
    def get_object_types(self) -> list[str]: ...

@runtime_checkable
class ClarifyMessageProvider(Protocol):
    def get_message(self, reason: ClarifyReason, state: DialogueState) -> str: ...

class Plugin(FlowProvider, ActionProvider, IntentProvider, SchemaProvider, ClarifyMessageProvider, Protocol):
    name: str