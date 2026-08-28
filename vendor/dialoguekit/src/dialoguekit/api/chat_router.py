"""
定义路由
"""
import uuid
from dataclasses import dataclass
from fastapi import APIRouter, Depends

from dialoguekit.api.schemas import ChatResponse, ChatRequest, ChatBotMessage, ChatObject
from dialoguekit.domain.messages import UserMessage, ProcessedResult, MessageType, FocusedObject
from dialoguekit.api.dependencies import DialogueStateServiceDep

router = APIRouter()


@router.get("/")
def hello_endpoint():
    return {"success": "ok"}


@dataclass(slots=True)
class User:
    name: str
    age: int
    address: str


@router.get("/test", response_model=User)
def test_endpoint():
    return {
        "name": "zs",
        "age": "18",
        "address": "sz",
        "card_no": "xxxxxxxabcdddddddd"
    }


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest,
                        service: DialogueStateServiceDep):
    user_message = _build_user_message(chat_request)
    processed_result = await service.process_message(user_message)
    chat_response = _build_chat_response(processed_result)
    return chat_response


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=str(uuid.uuid4().hex),
        type=MessageType.OBJECT if chat_request.object is not None else MessageType.TEXT,
        text=chat_request.text,
        object=FocusedObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object is not None else None
    )


def _build_chat_response(processed_result: ProcessedResult) -> ChatResponse:
    return ChatResponse(
        message_id=processed_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_message.text,
                object=ChatObject(
                    id=bot_message.object.id,
                    type=bot_message.object.type,
                    title=bot_message.object.title,
                    attributes=bot_message.object.attributes
                ) if bot_message.object is not None else None
            )
            for bot_message in processed_result.messages
        ]
    )