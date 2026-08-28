"""知识库：切块/向量化/索引构建/两级检索（FAQ 精确层 + 语义召回层）。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

FAQ_SIM_THRESHOLD = 0.78
SEMANTIC_SIM_THRESHOLD = 0.60
TOP_K = 4

PROJECT_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"


@dataclass
class Chunk:
    kb_type: str
    source: str
    content: str
    embedding: list[float] = field(default_factory=list)
    title: str | None = None
    id: int | None = None


# --------------------------------------------------------------------------- #
# 1. 切块
# --------------------------------------------------------------------------- #
def _as_embeddings(value) -> list[float]:
    """将 JSON 列读回的向量统一为 list[float]。"""
    if isinstance(value, str):
        import json as _json

        value = _json.loads(value)
    return [float(x) for x in value]

def load_faq_entries() -> list[dict]:
    entries: list[dict] = []
    path = KNOWLEDGE_DIR / "faq.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def chunk_faq() -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, entry in enumerate(load_faq_entries()):
        q = entry.get("question", "")
        a = entry.get("answer", "")
        chunks.append(
            Chunk(
                kb_type="faq",
                source=f"faq.jsonl#{idx}",
                title=q,
                content=f"问：{q}\n答：{a}",
            )
        )
    return chunks


def split_md_document(text: str) -> list[tuple[str, str]]:
    """按标题切分文档，返回 [(title, body)]。"""
    sections: list[tuple[str, str]] = []
    current_title = "概述"
    buf: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if buf:
                sections.append((current_title, "\n".join(buf).strip()))
                buf = []
            current_title = re.sub(r"^#{1,4}\s+", "", line).strip()
        else:
            buf.append(line)
    if buf:
        sections.append((current_title, "\n".join(buf).strip()))
    return [(t, b) for t, b in sections if b]


def split_long_text(text: str, max_len: int = 500, overlap: int = 50) -> list[str]:
    if len(text) <= max_len:
        return [text] if text.strip() else []
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        parts.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return parts


def chunk_docs() -> list[Chunk]:
    chunks: list[Chunk] = []
    for md_path in sorted((KNOWLEDGE_DIR / "docs").rglob("*.md")):
        rel = md_path.relative_to(KNOWLEDGE_DIR / "docs")
        kb_type = rel.parts[0]  # products / policy
        text = md_path.read_text(encoding="utf-8")
        for title, body in split_md_document(text):
            for part in split_long_text(body):
                chunks.append(Chunk(kb_type=kb_type, source=str(rel), title=title, content=part))
    return chunks


def build_chunks() -> list[Chunk]:
    return chunk_faq() + chunk_docs()


# --------------------------------------------------------------------------- #
# 2. 运行时检索
# --------------------------------------------------------------------------- #
class KnowledgeBase:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    async def load_once(self) -> None:
        if self._loaded:
            return
        from sqlalchemy import select

        import app.database as db

        assert db.session_factory is not None, "数据库引擎未初始化"
        async with db.session_factory() as session:
            stmt = select(db.KbChunkRecord).where(db.KbChunkRecord.yn == 1)
            rows = (await session.execute(stmt)).scalars().all()
        self._chunks = [
            Chunk(
                id=r.id,
                kb_type=r.kb_type,
                source=r.source,
                title=r.title,
                content=r.content,
                embedding=[float(x) for x in _as_embeddings(r.embedding)],
            )
            for r in rows
        ]
        self._loaded = True

    def search(self, query_vec: list[float], top_k: int = TOP_K) -> dict:
        """两级检索：FAQ 精确层（>=0.85 直出）+ 语义召回层（>=0.60 top_k）。"""
        if not self._chunks:
            return {"faq_hits": [], "semantic_hits": []}
        q = np.asarray(query_vec, dtype=np.float32)
        mat = np.asarray([c.embedding for c in self._chunks], dtype=np.float32)
        sims = (mat @ q).tolist()

        faq_hits = [
            {"chunk": c, "score": s}
            for c, s in zip(self._chunks, sims)
            if c.kb_type == "faq" and s >= FAQ_SIM_THRESHOLD
        ]
        faq_hits.sort(key=lambda x: -x["score"])

        ranked = [
            {"chunk": c, "score": s}
            for c, s in zip(self._chunks, sims)
            if s >= SEMANTIC_SIM_THRESHOLD
        ]
        ranked.sort(key=lambda x: -x["score"])
        return {"faq_hits": faq_hits, "semantic_hits": ranked[:top_k]}

