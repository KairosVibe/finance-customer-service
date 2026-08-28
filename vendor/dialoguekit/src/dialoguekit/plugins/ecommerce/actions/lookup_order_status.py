from typing import Any
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action, ActionResult
from dialoguekit.domain.messages import BotMessage
from dialoguekit.infrastructure.http_client import http_client
from dialoguekit.config.settings import settings


class ActionLookupOrderStatus(Action):
    name = "action_lookup_order_status"

    async def run(self, action_kwargs: dict[str, Any], state: DialogueState) -> ActionResult:
        order_number = state.active_task.slots.get('order_number')
        if not order_number:
            return ActionResult(messages=[BotMessage(text="订单号为空")])

        try:
            response = await http_client.get(f"{settings.commerce_api_base_url}/orders/{order_number}")
            data = response.json().get('data', {})

            return ActionResult(
                messages=[],
                updated_slots={
                    "order_number": order_number,
                    "order_status": data.get("status", "未知"),
                    "order_summary": data.get("summary", ""),
                }
            )
        except Exception as e:
            return ActionResult(messages=[BotMessage(text=f"查询订单失败: {str(e)}")])