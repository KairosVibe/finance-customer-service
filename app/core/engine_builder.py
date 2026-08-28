"""装配 DialogueEngine（P3：金融流程 + 业务 Action + RAG + 闲聊 + 规则兜底）。"""
from __future__ import annotations

from pathlib import Path

import dialoguekit
from dialoguekit.clarify.responder import ClarifyResponder
from dialoguekit.engines.dialogue_engine import DialogueEngine
from dialoguekit.plan.validator import TurnPlanValidator
from dialoguekit.task.action.builtin.listener import ActionListener
from dialoguekit.task.action.builtin.response import ActionResponse
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.task.action.runner import ActionRunner
from dialoguekit.task.commands.processor import CommandProcessor
from dialoguekit.task.flows.executor import FlowExecutor
from dialoguekit.task.flows.loader import FlowLoader
from dialoguekit.task.handler import TaskHandler

from app.actions.finance_actions import (
    ActionCardLoss,
    ActionCreateTicket,
    ActionLookupAccount,
    ActionLookupTransactions,
    ActionSubmitLoan,
)
from app.core.chitchat import FinanceChitChatHandler
from app.core.clarify import FinanceClarifyMessageProvider
from app.core.intent import RobustTurnPlanner
from app.core.knowledge import FINANCE_KNOWLEDGE_INTENTS, FinanceKnowledgeHandler
from app.rag.knowledge_base import KnowledgeBase

PROJECT_DIR = Path(__file__).resolve().parents[2]  # customer-service 根目录
SYSTEM_FLOWS_PATH = Path(dialoguekit.__file__).resolve().parents[1] / "flow_config" / "system_flows.yml"
USER_FLOWS_PATH = PROJECT_DIR / "app" / "flow_config" / "user_flows.yml"


def build_dialogue_engine() -> DialogueEngine:
    # 1. 加载系统流程 + 金融业务流程
    flow_list = FlowLoader().load_multi_yaml([SYSTEM_FLOWS_PATH, USER_FLOWS_PATH])

    # 2. 注册动作：内置 + 金融业务
    register = ActionRegister()
    register.registry_action(ActionListener())
    register.registry_action(ActionResponse())
    register.registry_action(ActionLookupAccount())
    register.registry_action(ActionLookupTransactions())
    register.registry_action(ActionSubmitLoan())
    register.registry_action(ActionCardLoss())
    register.registry_action(ActionCreateTicket())
    action_runner = ActionRunner(register)

    return DialogueEngine(
        turn_planner=RobustTurnPlanner(),
        turn_plan_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(message_provider=FinanceClarifyMessageProvider()),
        task_handler=TaskHandler(
            flow_list=flow_list,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner=action_runner,
        ),
        knowledge_handler=FinanceKnowledgeHandler(
            knowledge_intents=FINANCE_KNOWLEDGE_INTENTS,
            knowledge_base=KnowledgeBase(),
        ),
        chitchat_handler=FinanceChitChatHandler(),
    )
