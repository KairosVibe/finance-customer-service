"""金融业务 Action（P3）：账户/交易查询 + 贷款申请/信用卡挂失/投诉工单写入。"""
from __future__ import annotations

import re
import time

from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action, ActionResult
from sqlalchemy import select

import app.database as db
from app.risk.guard import risk_guard
from app.tools.finance_client import (
    create_support_ticket,
    get_account,
    get_credit_limit,
    get_transactions,
    submit_loan_application,
)


async def _customer_no(session_id: str) -> str | None:
    if db.session_factory is None:
        return None
    try:
        async with db.session_factory() as session:
            rec = (
                await session.execute(
                    select(db.SessionRecord).where(db.SessionRecord.session_id == session_id)
                )
            ).scalar_one_or_none()
            return rec.customer_no if rec else None
    except Exception:
        return None


def _to_amount(value, default: float = 0.0) -> float:
    """金额归一化：支持“10万”“1.5亿”等中文单位。"""
    s = str(value or "").replace(",", "").strip()
    if not s:
        return default
    multiplier = 1.0
    if s.endswith("万"):
        multiplier = 10000.0
        s = s[:-1]
    elif s.endswith("亿"):
        multiplier = 100000000.0
        s = s[:-1]
    try:
        return float(s) * multiplier
    except ValueError:
        return default

def _to_int(value, default: int = 12) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else default



def _record_tool(state, name: str) -> None:
    """链路可观测：记录工具调用（供 cs_trace 与调试区使用）。"""
    state.context.setdefault("_trace_tools", []).append(name)

class ActionLookupAccount(Action):
    name = "action_lookup_account"

    async def run(self, action_kwargs: dict, state: DialogueState) -> ActionResult:
        _record_tool(state, self.name)
        assert state.active_task is not None
        account_no = state.active_task.slots.get("account_no")
        customer_no = await _customer_no(state.sender_id) or ""
        data = await get_account(account_no, customer_no)
        if not data:
            return ActionResult(updated_slots={
                "account_balance": "未知",
                "account_frozen_amount": "未知",
                "account_available_balance": "未知",
            })
        balance = data.get("balance_amount", "0.00")
        frozen = data.get("frozen_amount", "0.00")
        try:
            available = f"{float(balance) - float(frozen):.2f}"
        except ValueError:
            available = balance
        # 上下文保持：验证通过的账户号在后续任务自动复用
        state.context["account_no"] = account_no
        return ActionResult(updated_slots={
            "account_balance": balance,
            "account_frozen_amount": frozen,
            "account_available_balance": available,
        })


class ActionLookupTransactions(Action):
    name = "action_lookup_transactions"

    async def run(self, action_kwargs: dict, state: DialogueState) -> ActionResult:
        _record_tool(state, self.name)
        assert state.active_task is not None
        account_no = state.active_task.slots.get("account_no")
        customer_no = await _customer_no(state.sender_id) or ""
        items = await get_transactions(account_no, customer_no)
        if not items:
            return ActionResult(updated_slots={
                "transactions_summary": f"未查询到账户 {account_no} 的交易记录，请核对账户号后重试。",
            })
        lines = []
        for it in items[:5]:
            at = it.get("transaction_at", "")
            ttype = it.get("transaction_type", "")
            amt = it.get("transaction_amount", "0")
            cp = it.get("counterparty_name", "")
            lines.append(f"{at}  {ttype}  {amt} 元（{cp}）")
        state.context["account_no"] = account_no
        return ActionResult(updated_slots={
            "transactions_summary": f"账户 {account_no} 最近 {len(lines)} 笔交易：\n" + "\n".join(lines),
        })


class ActionSubmitLoan(Action):
    name = "action_submit_loan"

    async def run(self, action_kwargs: dict, state: DialogueState) -> ActionResult:
        _record_tool(state, self.name)
        assert state.active_task is not None
        customer_no = await _customer_no(state.sender_id) or ""
        slots = state.active_task.slots

        blocked = await risk_guard.pre_check(self.name, state)
        if blocked:
            return ActionResult(updated_slots={"loan_result": blocked})

        # 贷款申请前置依赖：授信额度检查
        limit = await get_credit_limit(customer_no)
        if not limit:
            return ActionResult(updated_slots={
                "loan_result": "您当前暂无可用授信额度。可先通过手机银行“贷款-申请授信”办理授信，获得额度后再提交贷款申请。",
            })

        request_no = f"{state.sender_id}:loan:{int(time.time())}"
        try:
            data = await submit_loan_application(
                {
                    "request_no": request_no,
                    "customer_no": customer_no,
                    "limit_no": limit.get("limit_no"),
                    "apply_amount": _to_amount(slots.get("apply_amount")),
                    "apply_term_months": _to_int(slots.get("apply_term_months"), 12),
                    "repayment_method": slots.get("repayment_method", "equal_installment"),
                    "loan_purpose": slots.get("loan_purpose", "consume"),
                },
                customer_no,
            )
            app_no = (data or {}).get("application_no") or "已受理"
            reply = f"您的贷款申请已提交，申请编号 {app_no}。预计 1-3 个工作日完成审批，请留意手机银行通知。"
            return ActionResult(updated_slots={"loan_result": risk_guard.post_check(reply)})
        except Exception as exc:
            return ActionResult(updated_slots={"loan_result": f"贷款申请提交失败：{exc}"})


class ActionCardLoss(Action):
    name = "action_card_loss"

    async def run(self, action_kwargs: dict, state: DialogueState) -> ActionResult:
        _record_tool(state, self.name)
        assert state.active_task is not None
        customer_no = await _customer_no(state.sender_id) or ""
        slots = state.active_task.slots

        blocked = await risk_guard.pre_check(self.name, state)
        if blocked:
            return ActionResult(updated_slots={"loss_result": blocked})

        request_no = f"{state.sender_id}:loss:{int(time.time())}"
        try:
            data = await create_support_ticket(
                {
                    "request_no": request_no,
                    "customer_no": customer_no,
                    "ticket_type": "card_loss",
                    "ticket_title": "信用卡挂失",
                    "ticket_content": (
                        f"卡号：{slots.get('card_no')}；挂失原因：{slots.get('loss_reason')}；"
                        f"身份验证信息：{slots.get('identity_info')}"
                    ),
                    "related_type": "none",
                    "related_id": None,
                },
                customer_no,
            )
            ticket_no = (data or {}).get("ticket_no") or "已受理"
            reply = (
                f"您的信用卡挂失申请已受理，工单号 {ticket_no}。挂失生效后该卡将立即止付，"
                "因盗刷产生的损失由银行承担，请尽快通过手机银行或网点补办新卡。"
            )
            return ActionResult(updated_slots={"loss_result": risk_guard.post_check(reply)})
        except Exception as exc:
            return ActionResult(updated_slots={"loss_result": f"挂失申请提交失败：{exc}"})


class ActionCreateTicket(Action):
    name = "action_create_ticket"

    async def run(self, action_kwargs: dict, state: DialogueState) -> ActionResult:
        _record_tool(state, self.name)
        assert state.active_task is not None
        customer_no = await _customer_no(state.sender_id) or ""
        slots = state.active_task.slots

        blocked = await risk_guard.pre_check(self.name, state)
        if blocked:
            return ActionResult(updated_slots={"ticket_result": blocked})

        request_no = f"{state.sender_id}:ticket:{int(time.time())}"
        try:
            data = await create_support_ticket(
                {
                    "request_no": request_no,
                    "customer_no": customer_no,
                    "ticket_type": slots.get("ticket_type") or "complaint",
                    "ticket_title": f"投诉工单：{slots.get('ticket_type')}",
                    "ticket_content": (
                        f"关联交易号：{slots.get('transaction_no') or '无'}；"
                        f"问题描述：{slots.get('description')}"
                    ),
                    "related_type": "none",
                    "related_id": None,
                },
                customer_no,
            )
            ticket_no = (data or {}).get("ticket_no") or "已受理"
            reply = (
                f"您的投诉工单已创建，工单号 {ticket_no}。"
                "我行将在 3 个工作日内受理反馈，复杂投诉不超过 15 个工作日处理完毕。"
            )
            return ActionResult(updated_slots={"ticket_result": risk_guard.post_check(reply)})
        except Exception as exc:
            return ActionResult(updated_slots={"ticket_result": f"工单创建失败：{exc}"})








