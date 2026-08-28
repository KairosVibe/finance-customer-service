"""RAG 回答生成：强制引用 + 无依据拒答。"""
from __future__ import annotations

RAG_SYSTEM = """你是中州银行智能客服。请仅依据下面提供的资料回答用户问题，回答末尾标注引用编号 [n]（n 为资料编号）。
规则：
1. 涉及收益率、利率、手续费、期限等数字必须与资料原文一致，禁止自行计算或估计；
2. 资料未覆盖用户问题时，明确回答：“这个问题我暂时没有找到准确答案，可以为您转人工客服。”不要编造；
3. 回答自然、简洁，不要提及“资料”“检索”等内部过程。

资料：
{chunks}
"""


def format_chunks(hits: list[dict]) -> str:
    lines = []
    for i, hit in enumerate(hits, 1):
        lines.append(f"[{i}] {hit['chunk'].content}")
    return "\n\n".join(lines)


async def answer_with_rag(query: str, hits: list[dict], llm_client) -> str:
    """基于检索结果生成回答（llm_client 为 LangChain 对话模型）。"""
    chunks_text = format_chunks(hits)
    messages = [
        {"role": "system", "content": RAG_SYSTEM.format(chunks=chunks_text)},
        {"role": "user", "content": query},
    ]
    resp = await llm_client.ainvoke(messages)
    return str(resp.content)
