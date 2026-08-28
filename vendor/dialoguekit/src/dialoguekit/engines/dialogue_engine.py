import time

from dialoguekit.chitchat.handler import ChitChatHandler
from dialoguekit.clarify.responder import ClarifyResponder
from dialoguekit.domain.messages import ProcessedResult, BotMessage, UserMessage, MessageType, FocusedObject
from dialoguekit.domain.state import DialogueState
from dialoguekit.knowledge.handler import KnowledgeHandler
from dialoguekit.plan.planner import TurnPlanner
from dialoguekit.plan.turn_plan import TurnPlan, ClarifyReason
from dialoguekit.plan.validator import TurnPlanValidator
from dialoguekit.task.commands.command import Command, SetSlotsCommand
from dialoguekit.task.flows.flows import FlowList
from dialoguekit.task.flows.steps import CollectionFlowStep
from dialoguekit.task.handler import TaskHandler


class DialogueEngine:

    def __init__(self,
                 turn_planner: TurnPlanner,
                 turn_plan_validator: TurnPlanValidator,
                 clarify_responder: ClarifyResponder,
                 task_handler: TaskHandler,
                 knowledge_handler: KnowledgeHandler,
                 chitchat_handler: ChitChatHandler
                 ):
        self.turn_planner = turn_planner
        self.turn_plan_validator = turn_plan_validator
        self.clarify_responder = clarify_responder
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler

    async def handle_message(self,
                             user_message: UserMessage,
                             dialogue_state: DialogueState) -> ProcessedResult:
        # 1. 准备session
        self._prepare_session(dialogue_state)

        # 2. 开启turn
        self._start_turn(user_message, dialogue_state)

        # 3. 消息分流（文本消息 or 对象消息）
        # 3.1 文本消息类型
        if user_message.type is MessageType.TEXT:
            bot_messages = await self._handle_text_message(dialogue_state)

        # 3.2 对象消息类型
        else:
            # a) 将点击的卡片存储到对话状态中
            dialogue_state.focused_object = user_message.object

            # b) 真正处理对象消息
            bot_messages = await self._handle_object_message(user_message.object, dialogue_state,
                                                             self.task_handler.flow_list)

        # 4. 提交
        dialogue_state.pending_turn.bot_messages = bot_messages
        dialogue_state.commit_pending_turn()

        # 5. 返回机器人回复的消息
        return ProcessedResult(message_id=user_message.message_id, messages=bot_messages)

    def _prepare_session(self,
                         state: DialogueState):
        current_session = state.current_session()
        if current_session is None:
            state.start_session()
        else:
            now = time.time()
            if now - current_session.activated_at > 60 * 60:
                state.close_current_session()
                state.reset_runtime_state_for_new_session()
                state.start_session()
            else:
                current_session.activated_at = now

    def _start_turn(self,
                    user_message: UserMessage,
                    state: DialogueState):
        state.begin_turn(user_message)

    async def _handle_text_message(self, dialogue_state: DialogueState) -> list[BotMessage]:
        turn_plan: TurnPlan = await self.turn_planner.predict(dialogue_state,
                                                              flow_list=self.task_handler.flow_list,
                                                              knowledge_intents=self.knowledge_handler.knowledge_intents)

        validated = self.turn_plan_validator.valid(turn_plan,
                                                   dialogue_state,
                                                   flow_list=self.task_handler.flow_list,
                                                   knowledge_intents=self.knowledge_handler.knowledge_intents
                                                   )
        if not validated.valid:
            return await self.clarify_responder.respond(validated.reason, dialogue_state)

        if turn_plan.task is not None:
            return await self.task_handler.handle(turn_plan.task.commands, dialogue_state)
        elif turn_plan.knowledge is not None:
            return await self.knowledge_handler.handle(turn_plan.knowledge.intents, dialogue_state)
        else:
            return await self.chitchat_handler.handle(turn_plan.chitchat.chat, dialogue_state)

    async def _handle_object_message(self,
                                     object: FocusedObject,
                                     dialogue_state: DialogueState,
                                     flow_list: FlowList) -> list[BotMessage]:
        command = self._try_build_set_slots_command(object, dialogue_state, flow_list)

        if command:
            return await self.task_handler.handle(commands=[command], dialogue_state=dialogue_state)

        if dialogue_state.active_task is not None:
            return await self.task_handler.handle(commands=[], dialogue_state=dialogue_state)

        return await self.clarify_responder.respond(reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
                                                    dialogue_state=dialogue_state)

    def _try_build_set_slots_command(self,
                                     object: FocusedObject,
                                     dialogue_state: DialogueState,
                                     flow_list: FlowList) -> Command | None:
        """业务对象消息 → 槽位填充（通用版）：
        当前活动流程处于 collect 步骤时，若对象属性或 id 能提供该槽位值，则自动填充。
        """
        task_context = dialogue_state.active_task
        if task_context is None:
            return None
        flow = flow_list.get_flow_by_id(task_context.flow_id)
        if flow is None:
            return None
        step = flow.get_step_by_id(task_context.step_id)
        if step is None or not isinstance(step, CollectionFlowStep):
            return None
        slot_name = step.slot_name
        value = None
        if object.attributes and slot_name in object.attributes:
            value = object.attributes[slot_name]
        if value is None:
            value = object.id
        if value is None:
            return None
        return SetSlotsCommand(command="set_slots", slots={slot_name: value})

    def _is_can_set_slots_command(self,
                                  slot_name: str,
                                  state: DialogueState,
                                  flow_list: FlowList) -> bool:
        task_context = state.active_task

        if task_context is None:
            return False

        flow = flow_list.get_flow_by_id(task_context.flow_id)
        if flow is None:
            return False

        step_id = task_context.step_id
        step = flow.get_step_by_id(step_id)
        if step is None:
            return False

        if not isinstance(step, CollectionFlowStep):
            return False

        return step.slot_name == slot_name
