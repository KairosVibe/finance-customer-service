"""链路日志：cs_trace 事件写入（intent/rag/tool_call/reply/state）。"""
from __future__ import annotations

import logging
from datetime import datetime

import app.database as db

logger = logging.getLogger(__name__)


async def trace_event(request_id: str, session_id: str, stage: str, detail: dict, cost_ms: int = 0) -> None:
    """写入一条链路日志；失败仅告警，不影响主流程。"""
    if not request_id:
        request_id = "unknown"
    try:
        assert db.session_factory is not None, "数据库引擎未初始化"
        async with db.session_factory() as session:
            session.add(
                db.TraceRecord(
                    request_id=request_id,
                    session_id=session_id,
                    stage=stage,
                    detail=detail or {},
                    cost_ms=cost_ms,
                    created_at=datetime.now(),
                )
            )
            await session.commit()
    except Exception:
        logger.warning("trace_event 写入失败: stage=%s", stage)
