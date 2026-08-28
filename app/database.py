"""customer_service 库：异步引擎、会话工厂与 ORM 模型（5 张表）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "cs_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_no: Mapped[str] = mapped_column(String(64), index=True)
    channel_code: Mapped[str] = mapped_column(String(32), default="MOBILE_BANK")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class MessageRecord(Base):
    __tablename__ = "cs_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    sender: Mapped[str] = mapped_column(String(16))
    message_type: Mapped[str] = mapped_column(String(32), default="text")
    content: Mapped[str] = mapped_column(Text)
    object_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class SessionStateRecord(Base):
    __tablename__ = "cs_session_state"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_no: Mapped[str] = mapped_column(String(64))
    state_json: Mapped[str] = mapped_column(Text)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class KbChunkRecord(Base):
    __tablename__ = "cs_kb_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_type: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(256))
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[dict] = mapped_column(JSON)
    yn: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class TraceRecord(Base):
    __tablename__ = "cs_trace"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON)
    cost_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime)


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db_engine() -> None:
    global engine, session_factory
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def dispose_engine() -> None:
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None



