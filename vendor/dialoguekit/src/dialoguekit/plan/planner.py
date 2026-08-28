import json
from dataclasses import asdict
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from dialoguekit.domain.contexts import TaskContext
from dialoguekit.domain.state import DialogueState
from dialoguekit.knowledge.intents import KnowledgeIntent
from dialoguekit.plan.turn_plan import TurnPlan
from dialoguekit.prompt.loader import load_prompt_template_content
from dialoguekit.infrastructure.llm_client import llm_client
from dialoguekit.chat_history.builder import ChatHistoryBuilder
from dialoguekit.task.flows.flows import FlowList


class TurnPlanner:
    async def predict(self,
                      dialogue_state: DialogueState,
                      *,
                      flow_list: FlowList,
                      knowledge_intents: dict[str, KnowledgeIntent]
                      ) -> TurnPlan:
        prompt_inputs: dict[str, Any] = self._build_prompt_inputs(dialogue_state,
                                                                   flow_list=flow_list,
                                                                   knowledge_intents=knowledge_intents)

        llm_result = await self._invoke(prompt_inputs)
        return llm_result

    def _build_prompt_inputs(self,
                             state: DialogueState,
                             *,
                             flow_list: FlowList,
                             knowledge_intents: dict[str, KnowledgeIntent]
                             ) -> dict[str, Any]:
        user_message_str = ChatHistoryBuilder.build_user_message_str(state.pending_turn.user_message)
        current_conversation_str = ChatHistoryBuilder.build(state.current_session().turns[-10:])
        focused_object_json = json.dumps(state.focused_object.to_dict(),
                                         ensure_ascii=False) if state.focused_object is not None else "null"
        interrupted_tasks_json = json.dumps(
            [TaskContext.to_dict(paused_task) for paused_task in state.paused_tasks], ensure_ascii=False)

        active_task_json = json.dumps(state.active_task.to_dict(),
                                      ensure_ascii=False) if state.active_task is not None else "null"

        available_flows_json = json.dumps({
            "flows": [
                {
                    k: v for k, v in asdict(flow_object).items() if k != "steps"
                } for flow_object in flow_list.flows if not flow_object.id.startswith("system_")
            ]
        }, ensure_ascii=False)

        knowledge_intents_json = json.dumps([{"id": intent_id, "description": knowledge_intent.description} for
                                             intent_id, knowledge_intent in knowledge_intents.items()],
                                            ensure_ascii=False)

        return {
            "user_message": user_message_str,
            "current_conversation": current_conversation_str,
            "focused_object_json": focused_object_json,
            "interrupted_tasks_json": interrupted_tasks_json,
            "active_task_json": active_task_json,
            "available_flows_json": available_flows_json,
            "knowledge_intents_json": knowledge_intents_json
        }

    async def _invoke(self, prompt_inputs: dict[str, Any]) -> TurnPlan:
        prompt_template_str = load_prompt_template_content("turn_plan")
        prompt_template = PromptTemplate.from_template(template=prompt_template_str, template_format="jinja2")
        chain = prompt_template | llm_client | JsonOutputParser()
        llm_result_dict = await chain.ainvoke(prompt_inputs)
        return TurnPlan.from_dict(llm_result_dict)