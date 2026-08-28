from typing import Any
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action, ActionResult
from dialoguekit.domain.messages import BotMessage, ChatObject
from dialoguekit.infrastructure.http_client import http_client
from dialoguekit.config.settings import settings


class ActionRecommendSimilarProducts(Action):
    name = "action_recommend_similar_products"

    async def run(self, action_kwargs: dict[str, Any], state: DialogueState) -> ActionResult:
        product_id = state.active_task.slots.get('product_id')
        if not product_id:
            return ActionResult(messages=[BotMessage(text="商品ID为空")])

        try:
            response = await http_client.get(f"{settings.commerce_api_base_url}/products/{product_id}")
            data = response.json().get('data', {})

            return ActionResult(
                messages=[
                    BotMessage(
                        text=f"为您推荐相似商品：{data.get('title', '相关商品')}",
                        object=ChatObject(
                            id=data.get('product_id', product_id),
                            title=data.get('title', '相似商品'),
                            type="product",
                            attributes={
                                "price": str(data.get('price', 0)),
                                "description": data.get('description', ''),
                            }
                        )
                    )
                ],
                updated_slots={}
            )
        except Exception as e:
            return ActionResult(messages=[BotMessage(text=f"推荐商品失败: {str(e)}")])