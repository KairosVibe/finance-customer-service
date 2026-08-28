"""
定义FastAPI实例
"""
from fastapi import FastAPI
from typing import Optional

from dialoguekit.api.chat_router import router
from dialoguekit.infrastructure.db_client import init_db_engine, dispose_engine
from dialoguekit.infrastructure.http_client import init_http_client, disposed_http_client
from dialoguekit.engines.dialogue_engine import DialogueEngine
from dialoguekit.task.action.register import ActionRegister


async def lifespan(_: FastAPI):
    print("应用启动的时候，来执行到回调函数")
    init_db_engine()
    init_http_client()

    yield

    print("应用关闭的时候，来执行到回调函数")
    await dispose_engine()
    await disposed_http_client()


def create_app(
    engine: Optional[DialogueEngine] = None,
    action_register: Optional[ActionRegister] = None
) -> FastAPI:
    app = FastAPI(description="通用智能客服框架 FASTAPI 实例", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()