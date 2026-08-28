"""FastAPI 依赖注入：引擎单例 + 会话仓储 + 服务。"""
from __future__ import annotations

from typing import Annotated

from dialoguekit.engines.dialogue_engine import DialogueEngine
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import database as db
from app.core.engine_builder import build_dialogue_engine
from app.repository.dialogue_repository import DialogueRepository
from app.services.dialogue_service import DialogueService

_engine: DialogueEngine | None = None


def get_engine() -> DialogueEngine:
    global _engine
    if _engine is None:
        _engine = build_dialogue_engine()
    return _engine


EngineDep = Annotated[DialogueEngine, Depends(get_engine)]


async def get_session():
    assert db.session_factory is not None, "数据库引擎未初始化"
    async with db.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_repository(session: SessionDep) -> DialogueRepository:
    return DialogueRepository(session)


RepositoryDep = Annotated[DialogueRepository, Depends(get_repository)]


def get_service(engine: EngineDep, repository: RepositoryDep) -> DialogueService:
    return DialogueService(engine, repository)


ServiceDep = Annotated[DialogueService, Depends(get_service)]
