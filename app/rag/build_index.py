"""构建知识库索引：python -m app.rag.build_index"""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import delete

import app.database as db
from app.rag.embedding import embed_texts
from app.rag.knowledge_base import build_chunks


async def main() -> None:
    db.init_db_engine()
    assert db.session_factory is not None
    async with db.session_factory() as session:
        await session.execute(delete(db.KbChunkRecord))
        chunks = build_chunks()
        texts = [c.content for c in chunks]
        print(f"[1/2] 切块完成：{len(chunks)} 个 chunk，开始向量化...")
        vectors = embed_texts(texts)
        now = datetime.now()
        for chunk, vec in zip(chunks, vectors):
            session.add(
                db.KbChunkRecord(
                    kb_type=chunk.kb_type,
                    source=chunk.source,
                    title=chunk.title,
                    content=chunk.content,
                    embedding=vec,
                    yn=1,
                    created_at=now,
                )
            )
        await session.commit()
        print(f"[2/2] 索引完成：已写入 {len(chunks)} 个 chunk 到 cs_kb_chunk")
    await db.dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
