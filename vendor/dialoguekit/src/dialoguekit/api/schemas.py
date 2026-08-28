"""
定义接口数据模型：和前端进行交互
继承BaseModel:在运行期间完成类型的校验和类型的转换
"""
from typing import Any

from pydantic import BaseModel, Field


class ChatObject(BaseModel):
    id: str
    title: str
    type: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatBotMessage(BaseModel):
    text: str
    object: ChatObject | None = None


class ChatRequest(BaseModel):
    sender_id: str
    text: str | None = None
    object: ChatObject | None = None


class ChatResponse(BaseModel):
    message_id: str
    messages: list[ChatBotMessage]