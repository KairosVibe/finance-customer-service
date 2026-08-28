from pathlib import Path
from typing import Optional, List

from dialoguekit.chitchat.handler import ChitChatHandler
from dialoguekit.clarify.responder import ClarifyResponder, DefaultClarifyMessageProvider
from dialoguekit.engines.dialogue_engine import DialogueEngine
from dialoguekit.knowledge.handler import KnowledgeHandler
from dialoguekit.plan.planner import TurnPlanner
from dialoguekit.plan.validator import TurnPlanValidator
from dialoguekit.task.commands.processor import CommandProcessor
from dialoguekit.task.flows.executor import FlowExecutor
from dialoguekit.task.flows.loader import FlowLoader
from dialoguekit.task.handler import TaskHandler
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.task.action.runner import ActionRunner
from dialoguekit.plugins.registry import plugin_registry
from dialoguekit.plugins.hooks import ClarifyMessageProvider

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[2]
FLOW_CONFIG_DIR = PROJECT_ROOT_DIR / "flow_config"


def build_dialogue_engine(
    plugin_registry_obj=None,
    extra_flow_files: Optional[List[str]] = None,
    action_register: Optional[ActionRegister] = None,
    clarify_provider: Optional[ClarifyMessageProvider] = None,
) -> DialogueEngine:
    registry = plugin_registry_obj or plugin_registry

    # 1. 加载核心系统流程
    core_flow_files = [FLOW_CONFIG_DIR / "system_flows.yml"]

    # 2. 加载插件提供的流程文件
    plugin_flow_files = registry.get_flow_files()

    # 3. 额外流程文件
    extra_files = [Path(f) for f in (extra_flow_files or [])]

    all_flow_files = core_flow_files + plugin_flow_files + extra_files
    flow_list = FlowLoader().load_multi_yaml(all_flow_files)

    # 4. 构建 ActionRegister（内置 + 插件 + 传入）
    if action_register is None:
        action_register = ActionRegister()
        from dialoguekit.task.action.builtin.listener import ActionListener
        from dialoguekit.task.action.builtin.response import ActionResponse

        action_register.registry_action(ActionListener())
        action_register.registry_action(ActionResponse())
        registry.register_all_actions(action_register)
    action_runner = ActionRunner(action_register)

    # 5. 合并 KnowledgeIntent
    from dialoguekit.knowledge.intents import KNOWLEDGE_INTENTS as CORE_INTENTS

    merged_intents = {**CORE_INTENTS, **registry.merge_intents()}

    # 6. ClarifyMessageProvider
    provider = clarify_provider or registry.get_clarify_provider() or DefaultClarifyMessageProvider()

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        turn_plan_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(message_provider=provider),
        task_handler=TaskHandler(
            flow_list=flow_list,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner=action_runner,
        ),
        knowledge_handler=KnowledgeHandler(knowledge_intents=merged_intents),
        chitchat_handler=ChitChatHandler(),
    )
