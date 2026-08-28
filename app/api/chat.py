"""对话 API：非流式 + SSE 流式（事件：status / delta / tool / done）。"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import ServiceDep
from app.api.response import fail, get_request_id, ok
from app.repository.dialogue_repository import SessionNotFoundError

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    session_id: str
    message: str | None = None
    message_type: str = "text"  # text | business_object
    payload: dict | None = None


@router.post("/chat")
async def chat(req: ChatRequest, request: Request, service: ServiceDep):
    rid = get_request_id(request)
    try:
        data = await service.process_message(req.session_id, req.message, req.message_type, req.payload, request_id=rid)
        return ok(data, rid)
    except SessionNotFoundError as exc:
        return fail(404, str(exc), rid)
    except Exception as exc:
        return fail(500, f"对话处理失败: {exc}", rid)


def _sse(etype: str, data: dict) -> str:
    payload = {"type": etype, **data}
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request, service: ServiceDep):
    rid = get_request_id(request)

    async def event_gen():
        try:
            yield _sse("status", {"stage": "intent", "message": "正在识别意图..."})
            result = await service.process_message(
                req.session_id, req.message, req.message_type, req.payload, request_id=rid
            )
            for tool in result.get("tools") or []:
                yield _sse("tool", {"name": tool})
            yield _sse("status", {"stage": "respond", "message": "正在生成回复..."})

            messages = result.get("messages") or []
            text = "\n".join(m.get("text", "") for m in messages)
            for i in range(0, len(text), 6):
                yield _sse("delta", {"text": text[i:i + 6]})
                await asyncio.sleep(0.01)

            yield _sse("done", {
                "message_id": result.get("message_id"),
                "messages": messages,
                "intent": result.get("intent"),
                "tools": result.get("tools"),
                "trace_id": rid,
            })
        except SessionNotFoundError as exc:
            yield _sse("error", {"message": str(exc)})
        except Exception as exc:
            yield _sse("error", {"message": f"处理失败: {exc}"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

