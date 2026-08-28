"""金融客服澄清文案。"""
from __future__ import annotations

from dialoguekit.domain.state import DialogueState
from dialoguekit.plan.turn_plan import ClarifyReason


class FinanceClarifyMessageProvider:
    def get_message(self, reason: ClarifyReason, state: DialogueState | None = None) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return "您是想先办理业务（如查账户、办贷款、挂失卡片），还是先咨询理财/贷款产品或政策信息呢？"
        if reason is ClarifyReason.MISSING_TRACK:
            return "我是金融客服助手，可以帮您查账户、查交易、咨询理财/贷款产品，或办理贷款申请、信用卡挂失、投诉工单。请问您需要哪项？"
        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return "您是想咨询金融产品信息，还是了解利率、手续费、还款等政策规则呢？"
        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return "您是想办理什么业务呢？比如账户查询、交易查询、贷款申请、信用卡挂失或提交投诉工单。"
        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先选择您要咨询的银行卡或账户，我再继续帮您查询。"
        if reason is ClarifyReason.UNKNOWN_TASK_FLOW:
            return "这个业务功能正在建设中，您可以先咨询理财产品、利率政策，或稍后再试。"
        return "我还没完全理解您的意思，您可以换个更具体的说法，比如“查一下账户余额”或“我要申请消费贷款”。"
