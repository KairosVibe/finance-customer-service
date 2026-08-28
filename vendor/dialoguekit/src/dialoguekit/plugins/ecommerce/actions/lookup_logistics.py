from typing import Any
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action, ActionResult
from dialoguekit.domain.messages import BotMessage
from dialoguekit.infrastructure.http_client import http_client
from dialoguekit.config.settings import settings


class ActionLookupLogistics(Action):
    name = "action_lookup_logistics"

    async def run(self, action_kwargs: dict[str, Any], state: DialogueState) -> ActionResult:
        order_number = state.active_task.slots.get('order_number')
        if not order_number:
            return ActionResult(messages=[BotMessage(text="订单号为空")])

        try:
            response = await http_client.get(f"{settings.commerce_api_base_url}/orders/{order_number}/logistics")
            data = response.json().get('data', {})

            return ActionResult(
                messages=[],
                updated_slots={
                    "order_number": order_number,
                    "logistics_company": data.get("logistics_company", "未知"),
                    "tracking_number": data.get("tracking_number", "未知"),
                    "logistics_status": data.get("status", "未知"),
                }
            )
        except Exception as e:
            return ActionResult(messages=[BotMessage(text=f"查询物流失败: {str(e)}")])