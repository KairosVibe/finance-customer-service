"""意图路由：LLM 多轨道路由 + 规则关键词兜底（LLM 不可用时服务不中断）。"""
from __future__ import annotations

from typing import Any

from dialoguekit.domain.state import DialogueState
from dialoguekit.plan.planner import TurnPlanner
from dialoguekit.plan.turn_plan import ChitChatTurnPlan, KnowledgeTurnPlan, TurnPlan

# 规则兜底：关键词 → 知识意图（P3 引入流程后补充任务意图）
_RULE_TABLE: list[tuple[tuple[str, ...], str]] = [
    (("理财", "基金", "存款", "大额存单", "结构性存款", "现金管理", "产品"), "product_consult"),
    (("贷款", "消费贷", "经营贷", "房贷", "利率", "年化"), "product_consult"),
    (("手续费", "提前还款", "还款规则", "免息期", "年费", "账单", "风险测评", "征信", "投诉", "客服"), "policy_consult"),
    (("余额", "账户", "交易", "流水"), "policy_consult"),
]


class RobustTurnPlanner(TurnPlanner):
    """LLM 路由；调用失败时按关键词规则兜底。"""

    async def predict(self, dialogue_state, *, flow_list, knowledge_intents):
        try:
            plan = await super().predict(
                dialogue_state, flow_list=flow_list, knowledge_intents=knowledge_intents
            )
        except Exception:
            plan = self._rule_fallback(dialogue_state, knowledge_intents)
        # 链路可观测：记录意图摘要（供 cs_trace 与调试区使用）
        dialogue_state.context["_trace_intent"] = self._summarize(plan)
        return plan

    @staticmethod
    def _summarize(plan: TurnPlan) -> dict[str, Any]:
        summary: dict[str, Any] = {"tracks": plan.activated_tracks()}
        if plan.task is not None:
            summary["commands"] = [getattr(c, "command", "") for c in plan.task.commands]
        if plan.knowledge is not None:
            summary["intents"] = plan.knowledge.intents
        if plan.chitchat is not None:
            summary["chitchat"] = True
        return summary

    def _rule_fallback(self, dialogue_state: DialogueState, knowledge_intents: dict) -> TurnPlan:
        text = ""
        if dialogue_state.pending_turn is not None and dialogue_state.pending_turn.user_message is not None:
            text = dialogue_state.pending_turn.user_message.text or ""
        for keywords, intent in _RULE_TABLE:
            if any(k in text for k in keywords) and intent in knowledge_intents:
                return TurnPlan(knowledge=KnowledgeTurnPlan(intents=[intent]))
        return TurnPlan(chitchat=ChitChatTurnPlan(chat=text or "您好"))

