import json
from typing import Any, Optional

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.plan.turn_plan import ClarifyReason
from dialoguekit.chat_history.builder import ChatHistoryBuilder
from dialoguekit.prompt.loader import load_prompt_template_content
from dialoguekit.infrastructure.llm_client import llm_client
from dialoguekit.plugins.hooks import ClarifyMessageProvider


class DefaultClarifyMessageProvider:
    def get_message(self, reason: ClarifyReason, state: DialogueState) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "你这次同时提到了多个方向。我们先处理一个，你想先办业务还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象，我再继续帮你看。"

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "你是想了解商品信息、订单信息，还是售后配送规则呢？"

        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先处理业务问题，还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "你这次是想办理什么业务呢？比如查订单、查物流，或者申请退款。"

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.focused_object
            if focused_object is not None and focused_object.type == "order":
                return "我已经收到这个订单了。你想查订单状态、查物流，还是申请退款呢？"
            if focused_object is not None and focused_object.type == "product":
                return "我已经收到这个商品了。你想了解它的商品信息、发货情况，还是售后相关问题呢？"

        return "我还需要再确认一下你的意思，你可以换个更具体的说法告诉我。"


class ClarifyResponder:
    def __init__(self, message_provider: Optional[ClarifyMessageProvider] = None):
        self.message_provider = message_provider or DefaultClarifyMessageProvider()

    async def respond(self,
                      reason: ClarifyReason,
                      dialogue_state: DialogueState) -> list[BotMessage]:
        prompt_inputs = self._build_prompt_inputs(reason, dialogue_state)
        rewritten = await self._invoke(prompt_inputs)
        return rewritten

    def _build_prompt_inputs(self,
                             reason: ClarifyReason,
                             state: DialogueState) -> dict[str, Any]:
        user_message_str = ChatHistoryBuilder.build_user_message_str(state.pending_turn.user_message)
        history_str = ChatHistoryBuilder.build(state.current_session().turns[-10:])
        focused_object_json = json.dumps(state.focused_object.to_dict(),
                                         ensure_ascii=False) if state.focused_object is not None else "null"

        clarify_message_str = self.message_provider.get_message(reason, state)
        return {
            "user_message": user_message_str,
            "history": history_str,
            "focused_object": focused_object_json,
            "clarify_message": clarify_message_str,
            "reason": reason.value
        }

    async def _invoke(self, prompt_inputs: dict[str, Any]) -> list[BotMessage]:
        prompt_template_str = load_prompt_template_content("clarify_respond")
        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format="jinja2")
        chain = prompt_template | llm_client | StrOutputParser()
        rewritten = await chain.ainvoke(prompt_inputs)
        return [BotMessage(text=rewritten)]