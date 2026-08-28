"""多会话仓储：cs_session / cs_message / cs_session_state。"""
from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from dialoguekit.domain.state import DialogueState
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import MessageRecord, SessionRecord, SessionStateRecord


class SessionNotFoundError(Exception):
    pass


class DialogueRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_session(
        self, customer_no: str, channel_code: str = "MOBILE_BANK", context: dict | None = None
    ) -> SessionRecord:
        now = datetime.now()
        session_id = uuid4().hex
        record = SessionRecord(
            session_id=session_id,
            customer_no=customer_no,
            channel_code=channel_code,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        state = DialogueState(sender_id=session_id)
        state_record = SessionStateRecord(
            session_id=session_id,
            customer_no=customer_no,
            state_json=json.dumps(state.to_dict(), ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False) if context else None,
            updated_at=now,
        )
        self._session.add(state_record)
        await self._session.commit()
        return record

    async def get_session(self, session_id: str) -> SessionRecord | None:
        stmt = select(SessionRecord).where(SessionRecord.session_id == session_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_sessions(self, customer_no: str) -> list[SessionRecord]:
        stmt = (
            select(SessionRecord)
            .where(SessionRecord.customer_no == customer_no)
            .order_by(SessionRecord.updated_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def load_state(self, session_id: str) -> DialogueState:
        stmt = select(SessionStateRecord).where(SessionStateRecord.session_id == session_id)
        record = (await self._session.execute(stmt)).scalar_one_or_none()
        if record is None:
            return DialogueState(sender_id=session_id)
        return DialogueState.from_dict(json.loads(record.state_json))

    async def load_state_record(self, session_id: str) -> SessionStateRecord | None:
        stmt = select(SessionStateRecord).where(SessionStateRecord.session_id == session_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def save_state(self, session_id: str, customer_no: str, dialogue_state: DialogueState) -> None:
        stmt = select(SessionStateRecord).where(SessionStateRecord.session_id == session_id)
        record = (await self._session.execute(stmt)).scalar_one_or_none()
        state_json = json.dumps(dialogue_state.to_dict(), ensure_ascii=False)
        now = datetime.now()
        if record is None:
            record = SessionStateRecord(
                session_id=session_id,
                customer_no=customer_no,
                state_json=state_json,
                updated_at=now,
            )
            self._session.add(record)
        else:
            record.state_json = state_json
            record.updated_at = now
            self._session.add(record)

        sess = await self.get_session(session_id)
        if sess is not None:
            sess.updated_at = now
            self._session.add(sess)
        await self._session.commit()

    async def append_message(
        self,
        session_id: str,
        sender: str,
        message_type: str,
        content: str,
        object_json: str | None = None,
    ) -> None:
        self._session.add(
            MessageRecord(
                session_id=session_id,
                sender=sender,
                message_type=message_type,
                content=content,
                object_json=object_json,
                created_at=datetime.now(),
            )
        )

    async def list_messages(
        self, session_id: str, page_no: int = 1, page_size: int = 20
    ) -> tuple[list[MessageRecord], int]:
        base = select(MessageRecord).where(MessageRecord.session_id == session_id)
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = base.order_by(MessageRecord.id.asc()).offset((page_no - 1) * page_size).limit(page_size)
        items = list((await self._session.execute(stmt)).scalars().all())
        return items, total
