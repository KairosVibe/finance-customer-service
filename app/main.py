"""金融智能客服服务入口（P1：会话 + 回显对话骨架）。"""
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn

from app.config import bootstrap_env, settings

bootstrap_env()  # 必须在导入 dialoguekit 相关模块之前执行

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import chat, sessions
from app.api.response import fail, get_request_id, ok
from app.database import dispose_engine, init_db_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_engine()
    yield
    await dispose_engine()


app = FastAPI(title="金融智能客服系统", version="0.1.0", lifespan=lifespan)
app.include_router(sessions.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return ok({"status": "up"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=fail(500, f"服务器内部错误: {exc}", get_request_id(request)),
    )



# 挂载单文件演示页（http://127.0.0.1:8100/）
from pathlib import Path as _Path

from fastapi.staticfiles import StaticFiles

app.mount(
    "/",
    StaticFiles(directory=_Path(__file__).resolve().parents[1] / "web", html=True),
    name="web",
)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)

