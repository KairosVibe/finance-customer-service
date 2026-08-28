"""统一响应：{code, message, request_id, data}（对齐 finance-data）。"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request


def new_request_id() -> str:
    return uuid4().hex


def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-Id") or new_request_id()


def ok(data: Any = None, request_id: str = "") -> dict:
    return {"code": 0, "message": "ok", "request_id": request_id, "data": data}


def fail(code: int, message: str, request_id: str = "") -> dict:
    return {"code": code, "message": message, "request_id": request_id, "data": None}
