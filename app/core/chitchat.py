"""闲聊兜底：金融人设 + 业务引导尾巴 + 连续 3 轮转人工提示。"""
from __future__ import annotations

from dialoguekit.chitchat.handler import ChitChatHandler
from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.infrastructure.llm_client import llm_client

CHITCHAT_SYSTEM = """你是“中州银行智能客服”，一家银行的线上智能客服。请用专业、自然、友好、简洁的中文回复客户的闲聊内容。
要求：
1. 回答简短（不超过 3 句话）；
2. 不要编造银行业务信息；
3. 不要回答与金融无关的专业问题。"""

GUIDANCE = "需要我帮您查一下账户或理财产品吗？"
MAX_CHITCHAT_TURNS = 3


class FinanceChitChatHandler(ChitChatHandler):
    async def handle(self, chat: str, dialogue_state: DialogueState) -> list[BotMessage]:
        text = await self._generate(chat)
        if self._consecutive_chitchat_turns(dialogue_state) >= MAX_CHITCHAT_TURNS:
            text += "\n\n如果问题比较复杂，也可以随时为您转接人工客服。"
        return [BotMessage(text=text)]

    async def _generate(self, chat: str) -> str:
        try:
            resp = await llm_client.ainvoke(
                [
                    {"role": "system", "content": CHITCHAT_SYSTEM},
                    {"role": "user", "content": chat},
                ]
            )
            text = str(resp.content).strip()
        except Exception:
            text = f"我是中州银行智能客服，很高兴为您服务！您说“{chat}”。"
        if GUIDANCE not in text:
            text = f"{text}\n{GUIDANCE}"
        return text

    def _consecutive_chitchat_turns(self, state: DialogueState) -> int:
        session = state.current_session()
        if session is None:
            return 0
        count = 0
        for turn in reversed(session.turns[-6:]):
            if any(GUIDANCE in b.text for b in turn.bot_messages):
                count += 1
            else:
                break
        return count
