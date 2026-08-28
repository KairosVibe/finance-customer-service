"""对话服务：会话管理 + 单轮对话闭环（加载状态→引擎→保存状态→记录消息→链路日志）。"""
from __future__ import annotations

import json
import time
from uuid import uuid4

from dialoguekit.domain.messages import (
    BotMessage,
    FocusedObject,
    MessageType,
    UserMessage,
)
from dialoguekit.engines.dialogue_engine import DialogueEngine

from app.observability.trace import trace_event
from app.repository.dialogue_repository import DialogueRepository, SessionNotFoundError
from app.risk.guard import risk_guard
from app.tools.finance_client import fetch_customer_profile


class DialogueService:
    def __init__(self, engine: DialogueEngine, repository: DialogueRepository):
        self._engine = engine
        self._repository = repository

    async def create_session(self, customer_no: str, channel_code: str = "MOBILE_BANK", request_id: str = "") -> dict:
        # 建会话时拉取客户档案，初始化上下文
        profile = await fetch_customer_profile(customer_no, request_id)
        record = await self._repository.create_session(customer_no, channel_code, context=profile)
        return {
            "session_id": record.session_id,
            "customer_no": record.customer_no,
            "channel_code": record.channel_code,
            "customer_name": profile.get("customer_name"),
            "created_at": record.created_at.isoformat(),
        }

    async def list_sessions(self, customer_no: str) -> list[dict]:
        records = await self._repository.list_sessions(customer_no)
        return [
            {
                "session_id": r.session_id,
                "customer_no": r.customer_no,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in records
        ]

    async def list_messages(self, session_id: str, page_no: int, page_size: int) -> dict:
        items, total = await self._repository.list_messages(session_id, page_no, page_size)
        return {
            "list": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "message_type": m.message_type,
                    "content": m.content,
                    "object": json.loads(m.object_json) if m.object_json else None,
                    "created_at": m.created_at.isoformat(),
                }
                for m in items
            ],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    async def get_state(self, session_id: str) -> dict:
        state = await self._repository.load_state(session_id)
        session = await self._repository.get_session(session_id)
        state_record = await self._repository.load_state_record(session_id)
        context = json.loads(state_record.context_json) if state_record and state_record.context_json else {}
        return {
            "session_id": session_id,
            "customer_no": session.customer_no if session else None,
            "context": context,
            "active_task": self._task_to_dict(state.active_task),
            "task_stack": [self._task_to_dict(t) for t in state.paused_tasks],
            "focused_object": state.focused_object.to_dict() if state.focused_object else None,
        }

    async def process_message(
        self, session_id: str, text: str | None, message_type: str, payload: dict | None, request_id: str = ""
    ) -> dict:
        session = await self._repository.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"会话不存在: {session_id}")

        message_id = uuid4().hex
        object_json: str | None = None
        if message_type == "business_object" and payload:
            user_message = UserMessage(
                sender_id=session_id,
                message_id=message_id,
                type=MessageType.OBJECT,
                object=FocusedObject(
                    id=payload.get("id") or "",
                    title=payload.get("title") or "",
                    type=payload.get("object_type") or "business_object",
                    attributes=payload,
                ),
            )
            object_json = json.dumps(payload, ensure_ascii=False)
            user_content = object_json
        else:
            user_message = UserMessage(
                sender_id=session_id,
                message_id=message_id,
                type=MessageType.TEXT,
                text=text or "",
            )
            user_content = text or ""

        await self._repository.append_message(
            session_id, "user", user_message.type.value, user_content, object_json
        )

        state = await self._repository.load_state(session_id)
        t0 = time.time()
        try:
            processed = await self._engine.handle_message(user_message, state)
        except Exception:
            bot_messages: list[BotMessage] = [
                BotMessage(text="系统开小差了，请稍后再试一次。")
            ]
            processed_message_id = message_id
        else:
            bot_messages = processed.messages or []
            processed_message_id = processed.message_id

        # 链路日志：intent / tool_call
        intent_info = state.context.pop("_trace_intent", None)
        if intent_info:
            await trace_event(request_id, session_id, "intent", intent_info, int((time.time() - t0) * 1000))
        tools = state.context.pop("_trace_tools", [])
        for tool in tools:
            await trace_event(request_id, session_id, "tool_call", {"action": tool})

        for bot in bot_messages:
            bot.text = risk_guard.post_check(bot.text)
            await self._repository.append_message(
                session_id,
                "assistant",
                "text",
                bot.text,
                json.dumps(bot.object.to_dict(), ensure_ascii=False) if bot.object else None,
            )

        await self._repository.save_state(session_id, session.customer_no, state)

        # 链路日志：reply / state
        await trace_event(
            request_id, session_id, "reply",
            {"message_id": processed_message_id, "messages": [b.text for b in bot_messages]},
        )
        await trace_event(
            request_id, session_id, "state",
            {
                "active_task": self._task_to_dict(state.active_task),
                "task_stack": [self._task_to_dict(t) for t in state.paused_tasks],
            },
        )

        return {
            "message_id": processed_message_id,
            "messages": [
                {"text": bot.text, "object": bot.object.to_dict() if bot.object else None}
                for bot in bot_messages
            ],
            "intent": intent_info,
            "tools": tools,
        }

    @staticmethod
    def _task_to_dict(task) -> dict | None:
        if task is None:
            return None
        return {"flow_id": task.flow_id, "step_id": task.step_id, "slots": getattr(task, "slots", {})}
