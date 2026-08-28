"""
负责：从注册中心根据action的名字找具体的Action对象，在执行找到Action对象的run方法
"""
from typing import Any
from dataclasses import dataclass, field

from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import ActionResult
from dialoguekit.task.action.register import ActionRegister


@dataclass(slots=True)
class ActionCall:
    action_name: str
    action_kwargs: dict[str, Any] = field(default_factory=dict)


class ActionRunner:

    def __init__(self, action_register: ActionRegister):
        self.action_register = action_register

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action = self.action_register.get_action(action_call.action_name)
        action_result = await action.run(action_call.action_kwargs, state)
        return action_result