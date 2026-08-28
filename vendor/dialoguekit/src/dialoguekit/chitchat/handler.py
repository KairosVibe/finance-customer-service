from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState


class ChitChatHandler:
    async def handle(self,
                     chat: str,
                     dialogue_state: DialogueState) -> list[BotMessage]:
        pass