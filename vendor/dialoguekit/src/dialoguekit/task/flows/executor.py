"""流程推进器：双层循环推进业务/系统流程（完整版）。

- 内层循环：推进到 action 步骤为止（_advance_flow_util_action）
- 外层循环：执行 action，收集回复与槽位更新
- action_listen 表示等待用户输入，停止推进
"""
from dataclasses import asdict

from dialoguekit.domain.contexts import SystemCollectInformationContext
from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.task.action.runner import ActionCall, ActionRunner
from dialoguekit.task.flows.flows import FlowList
from dialoguekit.task.flows.links import (
    FlowStepConditionLink,
    FlowStepFallbackLink,
    FlowStepStaticLink,
)
from dialoguekit.task.flows.steps import (
    ActionFlowStep,
    CollectionFlowStep,
    EndFlowStep,
    FlowStep,
    StartFlowStep,
)


class FlowExecutor:

    def __init__(self, action_runner: ActionRunner | None = None):
        self.action_runner = action_runner

    async def execute_flow(
        self,
        state: DialogueState,
        *,
        action_runner: ActionRunner | None = None,
        flow_list: FlowList,
    ) -> list[BotMessage]:
        runner = action_runner or self.action_runner
        final_response_messages: list[BotMessage] = []
        while True:
            # 1. 找到下一个 action 步骤
            action_call = self._advance_flow_util_action(state, flow_list)

            # 2. action_listen：等待用户输入，停止推进
            if action_call.action_name == "action_listen":
                break

            # 3. 执行 action，收集回复与槽位更新
            action_result = await runner.run(action_call, state)
            final_response_messages.extend(action_result.messages)
            state.set_slots(action_result.updated_slots)

        return final_response_messages

    def _advance_flow_util_action(self, state: DialogueState, flow_list: FlowList) -> ActionCall:
        while True:
            current_task = state.current_task()
            if current_task is None:
                return ActionCall(action_name="action_listen")

            flow_id = current_task.flow_id
            flow = flow_list.get_flow_by_id(flow_id)
            step_id = current_task.step_id
            step = flow.get_step_by_id(step_id)

            action_call = self._run_step(step, state)
            if action_call is not None:
                return action_call

    def _run_step(self, step: FlowStep, state: DialogueState) -> ActionCall | None:
        if isinstance(step, StartFlowStep):
            return self._run_start_step(step, state)
        elif isinstance(step, EndFlowStep):
            return self._run_end_step(state)
        elif isinstance(step, ActionFlowStep):
            return self._run_action_step(step, state)
        elif isinstance(step, CollectionFlowStep):
            return self.run_collection_step(step, state)
        return None

    def _run_start_step(self, step: StartFlowStep, state: DialogueState) -> None:
        self._advance_next_step(step, state)
        return None

    def _advance_next_step(self, step: FlowStep, state: DialogueState):
        next_step_id = self._find_next_step_id(step, state)
        state.current_task().step_id = next_step_id

    def _find_next_step_id(self, step: FlowStep, state: DialogueState) -> str:
        for link in step.next:
            if isinstance(link, FlowStepStaticLink):
                return link.target
            elif isinstance(link, FlowStepConditionLink):
                if self._eval_condition(link.condition, state):
                    return link.target
            elif isinstance(link, FlowStepFallbackLink):
                return link.target
        return ""

    def _eval_condition(self, condition_expr: str, state: DialogueState) -> bool:
        """执行 YAML 流程中配置的条件表达式（可信配置，仅限 slots/context 取值）。"""
        data = {
            "context": asdict(state.active_system_task) if state.active_system_task is not None else {},
            "slots": state.active_task.slots if state.active_task is not None else {},
        }
        return bool(eval(condition_expr, {}, data))

    def _run_end_step(self, state: DialogueState) -> None:
        if state.active_system_task is not None:
            state.end_system_task()
        elif state.active_task is not None:
            state.end_active_task()
        return None

    def _run_action_step(self, step: ActionFlowStep, state: DialogueState) -> ActionCall:
        self._advance_next_step(step, state)
        action_kwargs = step.args
        if isinstance(action_kwargs, str):
            # 例如 system_collect_information 的 args: context.response
            action_kwargs = asdict(state.active_system_task)["response"]
        return ActionCall(action_name=step.action, action_kwargs=action_kwargs)

    def run_collection_step(self, step: CollectionFlowStep, state: DialogueState) -> ActionCall | None:
        """collect 步骤：首次询问（激活 system_collect_information），再次校验并推进。"""
        if state.active_task.slots.get(step.slot_name):
            if step.validated:
                if self._eval_condition(condition_expr=step.validated.condition, state=state):
                    self._advance_next_step(step, state)
                    return None
                else:
                    state.remove_slot(step.slot_name)
                    if step.validated.failure_response:
                        return ActionCall(
                            action_name="action_response",
                            action_kwargs=asdict(step.validated.failure_response),
                        )
                    return ActionCall(
                        action_name="action_response",
                        action_kwargs={"text": "您填写的信息不合法，请重新填写。"},
                    )
            else:
                self._advance_next_step(step, state)
                return None
        else:
            state.start_system_task(
                SystemCollectInformationContext(
                    flow_id="system_collect_information",
                    step_id="start",
                    response=asdict(step.response),
                    slot_name=step.slot_name,
                )
            )
            return None
