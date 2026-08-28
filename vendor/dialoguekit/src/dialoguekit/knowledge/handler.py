from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.knowledge.intents import KnowledgeIntent


class KnowledgeHandler:
    def __init__(self, knowledge_intents: dict[str, KnowledgeIntent]):
        self.knowledge_intents = knowledge_intents

    async def handle(self,
                     intents: list[str],
                     dialogue_state: DialogueState) -> list[BotMessage]:
        pass