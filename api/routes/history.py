"""api/routes/history.py — GET /api/history endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from model.database import get_engine

router = APIRouter(prefix="/api", tags=["history"])


class HistoryItem(BaseModel):
    id: int
    question: str
    generated_sql: str | None
    latency_ms: int | None
    created_at: str


@router.get("/history", response_model=list[HistoryItem])
def history_endpoint() -> list[HistoryItem]:
    """Return the last 20 queries from query_log, newest first."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, question, generated_sql, latency_ms, created_at "
                "FROM query_log "
                "WHERE question != '[approved-write]' "
                "ORDER BY created_at DESC LIMIT 20"
            )
        ).fetchall()
    return [
        HistoryItem(
            id=row[0],
            question=row[1],
            generated_sql=row[2],
            latency_ms=row[3],
            created_at=str(row[4]),
        )
        for row in rows
    ]
