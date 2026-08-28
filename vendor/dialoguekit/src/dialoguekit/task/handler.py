"""业务流程轨道：命令处理器改状态 + 流程推进器读状态执行。"""
from __future__ import annotations

from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.base import Action  # noqa: F401  (保持类型引用)
from dialoguekit.task.action.register import ActionRegister
from dialoguekit.task.action.runner import ActionRunner
from dialoguekit.task.commands.command import Command
from dialoguekit.task.commands.processor import CommandProcessor
from dialoguekit.task.flows.executor import FlowExecutor
from dialoguekit.task.flows.flows import FlowList


class TaskHandler:

    def __init__(
        self,
        flow_list: FlowList,
        command_processor: CommandProcessor,
        flow_executor: FlowExecutor,
        action_runner: ActionRunner | None = None,
    ):
        self.flow_list = flow_list
        self.command_processor = command_processor
        self.flow_executor = flow_executor
        if action_runner is None:
            from dialoguekit.task.action.builtin.listener import ActionListener
            from dialoguekit.task.action.builtin.response import ActionResponse

            register = ActionRegister()
            register.registry_action(ActionListener())
            register.registry_action(ActionResponse())
            action_runner = ActionRunner(register)
        self.action_runner = action_runner

    async def handle(
        self,
        commands: list[Command],
        dialogue_state: DialogueState,
    ) -> list[BotMessage]:
        # 1. 改状态：处理四种命令（start_flow / set_slots / resume_flow / cancel_flow）
        self.command_processor.process_command(commands, dialogue_state, self.flow_list)

        # 2. 读状态：推进业务流程与系统流程
        bot_messages = await self.flow_executor.execute_flow(
            dialogue_state,
            action_runner=self.action_runner,
            flow_list=self.flow_list,
        )
        return bot_messages
