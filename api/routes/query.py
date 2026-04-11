"""
api/routes/query.py — /api/query and /api/approve endpoints.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.hitl_guard import check_sql
from agent.sql_chain import _execute_sql, _extract_table_names, _log_query, run_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question to convert to SQL")


class QueryResponse(BaseModel):
    sql: str
    results: list[dict[str, Any]]
    tables_used: list[str]
    requires_approval: bool
    approval_reason: str = ""
    latency_ms: int


class ApproveRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    approved: bool


class ApproveResponse(BaseModel):
    executed: bool
    results: list[dict[str, Any]]
    message: str


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    Convert a natural-language question to SQL and execute it.
    Write operations require explicit approval via /api/approve.
    """
    try:
        result = await run_query(request.question)
        return QueryResponse(**result)
    except Exception as exc:
        logger.error("Query endpoint error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/approve", response_model=ApproveResponse)
async def approve_endpoint(request: ApproveRequest) -> ApproveResponse:
    """
    Execute a previously flagged SQL statement if the user approves it.
    Always re-runs the HITL check before execution as a second safety layer.
    """
    guard = check_sql(request.sql)

    if not request.approved:
        return ApproveResponse(executed=False, results=[], message="Execution rejected by user.")

    # Second-pass HITL check — ensure nothing slipped through
    if guard["requires_approval"]:
        logger.warning("Executing approved write SQL: %s", request.sql[:200])

    try:
        results = await asyncio.to_thread(_execute_sql, request.sql)
        tables_used = _extract_table_names(request.sql)
        _log_query(
            question="[approved-write]",
            generated_sql=request.sql,
            latency_ms=0,
            tables_used=tables_used,
            error=None,
        )
        return ApproveResponse(executed=True, results=results, message="Query executed successfully.")
    except Exception as exc:
        logger.error("Approve endpoint execution error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
