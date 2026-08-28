"""知识检索处理：FAQ 精确层直出 + RAG 语义层引用回答 + 产品实时数据补充。"""
from __future__ import annotations

from dialoguekit.domain.messages import BotMessage
from dialoguekit.domain.state import DialogueState
from dialoguekit.infrastructure.llm_client import llm_client
from dialoguekit.knowledge.handler import KnowledgeHandler
from dialoguekit.knowledge.intents import KnowledgeIntent
from sqlalchemy import select

import app.database as db
from app.rag.answer import answer_with_rag
from app.rag.embedding import embed_query
from app.rag.knowledge_base import FAQ_SIM_THRESHOLD, KnowledgeBase
from app.tools.finance_client import search_products

# 金融知识意图（供给 LLM 路由与校验）
FINANCE_KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "product_consult": KnowledgeIntent(
        id="product_consult",
        description="存款/理财/基金/信用卡/贷款等金融产品咨询",
        provider_ids=["rag.product", "api.product"],
    ),
    "policy_consult": KnowledgeIntent(
        id="policy_consult",
        description="利率/手续费/提前还款/还款规则/风险提示等政策与FAQ咨询",
        provider_ids=["faq.finance", "rag.policy"],
    ),
    "general_finance_info": KnowledgeIntent(
        id="general_finance_info",
        description="金融通用信息咨询",
        provider_ids=["rag.policy"],
    ),
}


class FinanceKnowledgeHandler(KnowledgeHandler):
    def __init__(self, knowledge_intents=None, knowledge_base: KnowledgeBase | None = None):
        self.knowledge_intents = knowledge_intents or FINANCE_KNOWLEDGE_INTENTS
        self._kb = knowledge_base or KnowledgeBase()

    async def handle(self, intents: list[str], dialogue_state: DialogueState) -> list[BotMessage]:
        await self._kb.load_once()
        query = ""
        if dialogue_state.pending_turn is not None and dialogue_state.pending_turn.user_message is not None:
            query = dialogue_state.pending_turn.user_message.text or ""

        query_vec = embed_query(query)
        result = self._kb.search(query_vec)

        reply: str | None = None
        # 1. FAQ 精确层（相似度 >= 0.85 直接采用标准答案，保证利率/手续费类回答精确）
        if result["faq_hits"] and result["faq_hits"][0]["score"] >= FAQ_SIM_THRESHOLD:
            hit = result["faq_hits"][0]
            reply = hit["chunk"].content.split("答：", 1)[-1].strip()
        # 2. 语义召回层（RAG 生成，带引用 [n]）
        elif result["semantic_hits"]:
            reply = await answer_with_rag(query, result["semantic_hits"], llm_client)

        # 3. 产品咨询：补充 finance-data 实时产品数据
        if "product_consult" in intents:
            realtime = await self._product_realtime(query, dialogue_state)
            if realtime:
                reply = (reply + "\n\n" if reply else "") + "实时产品参考：\n" + realtime

        if not reply:
            reply = "这个问题我暂时没有找到准确答案，可以为您转人工客服。"

        return [BotMessage(text=reply)]

    async def _product_realtime(self, query: str, state: DialogueState) -> str:
        customer_no = await self._customer_no(state.sender_id)
        if not customer_no:
            return ""
        try:
            return await search_products(query, customer_no)
        except Exception:
            return ""

    async def _customer_no(self, session_id: str) -> str | None:
        if db.session_factory is None:
            return None
        try:
            async with db.session_factory() as session:
                rec = (
                    await session.execute(
                        select(db.SessionRecord).where(db.SessionRecord.session_id == session_id)
                    )
                ).scalar_one_or_none()
                return rec.customer_no if rec else None
        except Exception:
            return None
