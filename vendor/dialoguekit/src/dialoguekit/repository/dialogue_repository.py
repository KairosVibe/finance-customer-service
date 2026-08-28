import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert

from dialoguekit.domain.state import DialogueState
from dialoguekit.repository.dialogue_record import DialogueRecord


class OptimisticLockError(Exception):
    pass


class DialogueRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        stmt = select(DialogueRecord).where(DialogueRecord.sender_id == sender_id)
        cursor_result = await self._session.execute(stmt)
        dialogue_record = cursor_result.scalar_one_or_none()
        if dialogue_record is None:
            return DialogueState(sender_id=sender_id)

        dialogue_record_dict = json.loads(dialogue_record.state_json)
        return DialogueState.from_dict(dialogue_record_dict)

    async def save_state(self,
                         sender_id: str,
                         dialogue_state: DialogueState):
        dialogue_state_dict = dialogue_state.to_dict()
        dialogue_state_str = json.dumps(dialogue_state_dict, ensure_ascii=False)

        stmt = select(DialogueRecord).where(DialogueRecord.sender_id == sender_id)
        cursor = await self._session.execute(stmt)
        record = cursor.scalar_one_or_none()

        if record is None:
            new_record = DialogueRecord(sender_id=sender_id, state_json=dialogue_state_str, version=1)
            self._session.add(new_record)
        else:
            new_version = record.version + 1
            update_stmt = (
                update(DialogueRecord)
                .where(DialogueRecord.sender_id == sender_id)
                .where(DialogueRecord.version == record.version)
                .values(state_json=dialogue_state_str, version=new_version)
            )
            result = await self._session.execute(update_stmt)
            if result.rowcount == 0:
                raise OptimisticLockError(f"Concurrent modification for sender_id={sender_id}")

        await self._session.commit()