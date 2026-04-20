"""
api/routes/eval.py — POST /api/eval endpoint for RAGAS-style SQL evaluation.

Runs each question in the golden test set through the sql_chain pipeline,
compares execution results against the expected SQL, and persists per-run
results to the eval_log table.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.sql_chain import _execute_sql, _ensure_schema_exists, run_query
from model.database import get_session
from model.schema import Base, EvalLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["eval"])

_GOLDEN_SET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "eval_golden_set.json"
)


# ── Pydantic response models ─────────────────────────────────────────────────

class EvalResult(BaseModel):
    question_id: int
    question: str
    expected_sql: str
    generated_sql: str
    passed: bool
    latency_ms: int
    error: str | None


class EvalSummary(BaseModel):
    run_id: str
    total_questions: int
    passed: int
    failed: int
    accuracy_pct: float
    avg_latency_ms: float
    results: list[EvalResult]


# ── Result comparison helpers ────────────────────────────────────────────────

def _normalize_value(v: Any) -> str:
    """Stringify a cell value in a stable, type-agnostic way."""
    if v is None:
        return "__null__"
    if isinstance(v, Decimal):
        return str(round(float(v), 4))
    if isinstance(v, float):
        return str(round(v, 4))
    return str(v)


def _results_match(actual: list[dict], expected: list[dict]) -> bool:
    """
    Return True if both result sets contain the same multiset of rows.

    Column names are intentionally ignored so that equivalent queries with
    different aliases (e.g. 'cnt' vs 'total_orders') still pass.  Rows are
    compared as sorted tuples of normalised values so ordering differences
    don't cause false failures.
    """
    if len(actual) != len(expected):
        return False
    if not actual:
        return True

    def row_key(row: dict) -> tuple:
        return tuple(sorted(_normalize_value(v) for v in row.values()))

    return sorted(row_key(r) for r in actual) == sorted(row_key(r) for r in expected)


# ── Persistence ──────────────────────────────────────────────────────────────

def _save_eval_results(run_id: str, results: list[EvalResult]) -> None:
    """Write all per-question results for one eval run to eval_log."""
    try:
        _ensure_schema_exists()
        with get_session() as session:
            for r in results:
                session.add(
                    EvalLog(
                        run_id=run_id,
                        question_id=r.question_id,
                        question=r.question,
                        expected_sql=r.expected_sql,
                        generated_sql=r.generated_sql,
                        passed=r.passed,
                        latency_ms=r.latency_ms,
                        error=r.error,
                        created_at=datetime.utcnow(),
                    )
                )
            session.commit()
    except Exception as exc:
        logger.error("Failed to persist eval results: %s", exc)


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/eval/meta")
async def eval_meta() -> dict:
    """Return metadata about the golden test set (e.g. question count)."""
    try:
        golden_path = os.path.normpath(_GOLDEN_SET_PATH)
        with open(golden_path, "r", encoding="utf-8") as fh:
            golden_set: list[dict] = json.load(fh)
        return {"total_questions": len(golden_set)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load golden test set: {exc}")


@router.post("/eval", response_model=EvalSummary)
async def eval_endpoint() -> EvalSummary:
    """
    Run every question in the golden test set through the sql_chain pipeline.

    For each question:
      1. Run the question through run_query() to obtain generated SQL + results.
      2. Execute the expected SQL directly to obtain the reference result set.
      3. Compare both result sets (value-based, order-agnostic).
      4. Record pass/fail and latency.

    All results are persisted to eval_log and a summary is returned.
    """
    # Load golden test set
    try:
        golden_path = os.path.normpath(_GOLDEN_SET_PATH)
        with open(golden_path, "r", encoding="utf-8") as fh:
            golden_set: list[dict] = json.load(fh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load golden test set: {exc}")

    run_id = str(uuid.uuid4())
    results: list[EvalResult] = []

    for test_case in golden_set:
        question_id: int = test_case["id"]
        question: str = test_case["question"]
        expected_sql: str = test_case["expected_sql"]
        generated_sql = ""
        latency_ms = 0
        passed = False
        error: str | None = None

        try:
            # Step 1: run through the full LLM pipeline
            chain_result = await run_query(question)
            generated_sql = chain_result.get("sql", "")
            latency_ms = chain_result.get("latency_ms", 0)

            if chain_result.get("requires_approval"):
                error = "Generated SQL requires approval (write operation detected)"
            else:
                actual_results: list[dict] = chain_result.get("results", [])

                # Step 2: execute the expected SQL for the reference result set
                expected_results: list[dict] = await asyncio.to_thread(
                    _execute_sql, expected_sql
                )

                # Step 3: compare result sets
                passed = _results_match(actual_results, expected_results)

        except Exception as exc:
            error = str(exc)
            logger.warning("Eval question %d failed: %s", question_id, exc)

        results.append(
            EvalResult(
                question_id=question_id,
                question=question,
                expected_sql=expected_sql,
                generated_sql=generated_sql,
                passed=passed,
                latency_ms=latency_ms,
                error=error,
            )
        )

    # Persist to eval_log
    _save_eval_results(run_id, results)

    # Build summary
    total = len(results)
    n_passed = sum(1 for r in results if r.passed)
    avg_latency = sum(r.latency_ms for r in results) / total if total else 0.0

    return EvalSummary(
        run_id=run_id,
        total_questions=total,
        passed=n_passed,
        failed=total - n_passed,
        accuracy_pct=round(100.0 * n_passed / total, 1) if total else 0.0,
        avg_latency_ms=round(avg_latency, 1),
        results=results,
    )
