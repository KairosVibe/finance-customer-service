"""内置 action_response：渲染 YAML 文本（static / rephrase / generate 三种模式）。"""
from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from dialoguekit.chat_history.builder import ChatHistoryBuilder
from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.infrastructure.llm_client import llm_client
from dialoguekit.task.action.base import Action, ActionResult


class ActionResponse(Action):
    name = "action_response"

    async def run(self, action_kwargs: dict[str, Any], state: DialogueState) -> ActionResult:
        mode = action_kwargs.get("mode", "static")
        text = action_kwargs["text"]

        if mode == "rephrase":
            prompt = action_kwargs["prompt"]
            render_text = self._render_text(text, state)
            rewritten = await self._call_llm(prompt, state, render_text)
            return ActionResult(messages=[BotMessage(text=rewritten)])

        if mode == "generate":
            prompt = action_kwargs["prompt"]
            rewritten = await self._call_llm(prompt, state, render_text="")
            return ActionResult(messages=[BotMessage(text=rewritten)])

        render_text = self._render_text(text, state)
        return ActionResult(messages=[BotMessage(text=render_text)])

    def _render_text(self, text: str, state: DialogueState) -> str:
        template = Template(text)
        rendered = template.render(
            slots=state.active_task.slots if state.active_task is not None else None,
            context=state.active_system_task,
        )
        return rendered

    async def _call_llm(self, prompt_template_str: str, state: DialogueState, render_text: str = "") -> str:
        prompt_template = PromptTemplate.from_template(template=prompt_template_str)
        chain = prompt_template | llm_client | StrOutputParser()
        result = await chain.ainvoke(
            {
                "history": ChatHistoryBuilder.build(state.current_session().turns[-5:]),
                "user_message": ChatHistoryBuilder.build_user_message_str(state.pending_turn.user_message),
                "current_response": render_text,
            }
        )
        return result
