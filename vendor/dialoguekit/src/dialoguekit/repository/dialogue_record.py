from sqlalchemy.orm import Mapped, mapped_column
from dialoguekit.repository.base import Base
from sqlalchemy import TEXT, Integer

class DialogueRecord(Base):
    __tablename__ = "dialogue_states"

    sender_id: Mapped[str] = mapped_column(primary_key=True)
    state_json: Mapped[str] = mapped_column(TEXT, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)