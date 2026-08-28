from typing import Any
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action, ActionResult
from dialoguekit.domain.messages import BotMessage


class ActionEcho(Action):
    name = "action_echo"

    async def run(self, action_kwargs: dict[str, Any], state: DialogueState) -> ActionResult:
        text = action_kwargs.get("text", "Echo")
        for key, value in (state.active_task.slots.items() if state.active_task else {}):
            text = text.replace(f"{{{{ slots.{key} }}}}", str(value))
        return ActionResult(messages=[BotMessage(text=text)])