"""会话 API：创建/列表/历史/状态。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import ServiceDep
from app.api.response import fail, get_request_id, ok
from app.tools.finance_client import FinanceDataError

router = APIRouter(prefix="/api")


class CreateSessionRequest(BaseModel):
    customer_no: str = Field(min_length=1)
    channel_code: str = "MOBILE_BANK"


@router.post("/sessions")
async def create_session(req: CreateSessionRequest, request: Request, service: ServiceDep):
    rid = get_request_id(request)
    try:
        data = await service.create_session(req.customer_no, req.channel_code, request_id=rid)
        return ok(data, rid)
    except FinanceDataError:
        return fail(400, "客户不存在或状态异常，请核对客户号后重试", rid)
    except Exception as exc:
        return fail(500, f"创建会话失败: {exc}", rid)


@router.get("/customers/{customer_no}/sessions")
async def list_sessions(customer_no: str, request: Request, service: ServiceDep):
    rid = get_request_id(request)
    data = await service.list_sessions(customer_no)
    return ok(data, rid)


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: str,
    request: Request,
    service: ServiceDep,
    page_no: int = 1,
    page_size: int = 20,
):
    rid = get_request_id(request)
    data = await service.list_messages(session_id, page_no, page_size)
    return ok(data, rid)


@router.get("/sessions/{session_id}/state")
async def get_state(session_id: str, request: Request, service: ServiceDep):
    rid = get_request_id(request)
    data = await service.get_state(session_id)
    return ok(data, rid)
