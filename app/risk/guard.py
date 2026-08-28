"""风控提示中间件：前置状态预检 + 后置合规词扫描。"""
from __future__ import annotations

from dialoguekit.domain.state import DialogueState

FORBIDDEN_PROMISES = ("保本", "保收益", "稳赚", "无风险", "保证收益", "必涨", "稳赚不赔")
RISK_DISCLAIMER = "（温馨提示：投资有风险，请根据自身风险承受能力谨慎决策；以上内容不构成收益承诺。）"

WRITE_ACTIONS = ("action_submit_loan", "action_card_loss", "action_create_ticket")


class RiskGuard:
    def post_check(self, text: str) -> str:
        """后置：扫描违规承诺词，命中则追加风险提示。"""
        if any(w in text for w in FORBIDDEN_PROMISES) and RISK_DISCLAIMER not in text:
            return text + "\n" + RISK_DISCLAIMER
        return text

    async def pre_check(self, action_name: str, state: DialogueState) -> str | None:
        """前置：写入类动作的客户状态预检；返回风险提示语，None 表示通过。"""
        if action_name in WRITE_ACTIONS:
            customer_status = state.context.get("customer_status")
            if customer_status and customer_status != "normal":
                return "您的账户状态异常，暂时无法办理该业务，请联系人工客服核实处理。"
        return None


risk_guard = RiskGuard()
