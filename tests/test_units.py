"""单元测试（纯逻辑，不依赖 LLM/DB/embedding 模型）。运行：uv run pytest"""
from dialoguekit.plan.turn_plan import ClarifyReason

from app.actions.finance_actions import _to_amount, _to_int
from app.core.clarify import FinanceClarifyMessageProvider
from app.rag.knowledge_base import (
    build_chunks,
    chunk_faq,
    load_faq_entries,
    split_long_text,
    split_md_document,
)
from app.risk.guard import risk_guard


def test_to_amount():
    assert _to_amount("10万") == 100000.0
    assert _to_amount("1.5亿") == 150000000.0
    assert _to_amount("5,000") == 5000.0
    assert _to_amount("") == 0.0
    assert _to_amount("abc") == 0.0


def test_to_int():
    assert _to_int("24个月") == 24
    assert _to_int("12") == 12
    assert _to_int("") == 12


def test_split_long_text():
    text = "字" * 1200
    parts = split_long_text(text, max_len=500, overlap=50)
    assert len(parts) >= 3
    assert all(len(p) <= 500 for p in parts)


def test_split_md_document():
    md = "# 标题\n正文第一段。\n## 小节\n正文第二段。"
    sections = split_md_document(md)
    assert len(sections) == 2
    assert sections[0][0] == "标题"
    assert sections[1][0] == "小节"


def test_faq_seed():
    entries = load_faq_entries()
    assert len(entries) >= 40
    for e in entries:
        assert e.get("question") and e.get("answer")
    assert len(chunk_faq()) == len(entries)


def test_kb_chunks_nonempty():
    chunks = build_chunks()
    assert len(chunks) > len(chunk_faq())
    assert all(c.content for c in chunks)


def test_risk_post_check():
    t = risk_guard.post_check("这款产品保本保收益，稳赚不赔")
    assert "风险" in t
    t2 = risk_guard.post_check("您的账户余额正常。")
    assert "温馨提示" not in t2


def test_clarify_message():
    provider = FinanceClarifyMessageProvider()
    assert "账户" in provider.get_message(ClarifyReason.MISSING_TRACK, None)
    assert "办理业务" in provider.get_message(ClarifyReason.MULTIPLE_TRACKS, None)

