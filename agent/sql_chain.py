"""
sql_chain.py — LangChain LCEL pipeline: question → SQL → results.

# INTERN NOTE: LCEL chain composition explained
# LangChain Expression Language (LCEL) lets you compose chains using the pipe
# operator (|). Each component receives the output of the previous one as input.
# Our pipeline:
#   1. Retrieve relevant schema (RAG)     → inject into prompt context
#   2. Load few-shot YAML examples        → inject into prompt for in-context learning
#   3. Build ChatPromptTemplate           → structured system + user messages
#   4. Call LLM (temperature=0)           → deterministic, no creativity in SQL
#   5. Parse SQL from response            → extract the raw SQL string
#   6. HITL check                         → flag writes for human approval
#   7. Execute if approved (SELECT only)  → run against SQLite/PostgreSQL
#   8. Log to query_log                   → observability + debugging
#
# temperature=0 is critical: we want the most deterministic SQL possible.
# Any creativity in SQL generation leads to incorrect queries.
"""

import asyncio
import logging
import os
import re
import time
from datetime import datetime
from typing import Any

import yaml
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import text

from agent.hitl_guard import check_sql
from agent.retriever import get_relevant_schema
from model.database import get_engine, get_session
from model.schema import Base, QueryLog

load_dotenv()

logger = logging.getLogger(__name__)

_YAML_PATH = os.path.join(os.path.dirname(__file__), "few_shot_examples.yaml")

# Module-level LLM instance — reuses the underlying HTTP connection pool
# across all requests instead of creating a new client per query.
_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY", ""),
        )
    return _llm

SYSTEM_PROMPT = """You are an expert SQL analyst for the Olist Brazilian E-Commerce database.

Your task: Given a natural-language question, write a single, correct SQL SELECT query.

Rules:
1. Output ONLY the SQL query — no explanation, no markdown fences, no commentary.
2. Use only tables and columns present in the schema context below.
3. Use table aliases (e.g. fo for fact_orders, dp for dim_products).
4. Always qualify column names with table aliases.
5. For SQLite date operations use strftime(); never use DATE_TRUNC or EXTRACT.
6. Prefer NULLIF(x, 0) to avoid division-by-zero.
7. Limit results to 1000 rows unless the question asks for all rows.
8. Never generate INSERT, UPDATE, DELETE, or DROP statements.

--- RELEVANT SCHEMA ---
{schema}

--- FEW-SHOT EXAMPLES ---
{examples}
"""

USER_PROMPT = "Question: {question}\n\nSQL:"


def _load_few_shot_examples() -> str:
    """Load and format few-shot examples from the YAML file."""
    try:
        with open(_YAML_PATH, "r") as fh:
            data = yaml.safe_load(fh)
        lines: list[str] = []
        for ex in data.get("examples", []):
            lines.append(f"Q: {ex['question']}")
            lines.append(f"SQL: {ex['sql'].strip()}")
            lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to load few-shot examples: %s", exc)
        return ""


def _extract_sql(raw_response: str) -> str:
    """Strip markdown code fences and whitespace from the LLM response."""
    # Remove ```sql ... ``` or ``` ... ``` fences
    cleaned = re.sub(r"```(?:sql)?", "", raw_response, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    # Remove any leading "SQL:" label the model might add
    cleaned = re.sub(r"^SQL:\s*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _extract_table_names(sql: str) -> list[str]:
    """Heuristically extract table names referenced in a SQL query."""
    known_tables = {
        "fact_orders",
        "dim_users",
        "dim_products",
        "dim_sellers",
        "dim_geography",
        "dim_reviews",
    }
    sql_upper = sql.upper()
    found = [t for t in known_tables if t.upper() in sql_upper]
    return found


def _ensure_schema_exists() -> None:
    """Create all tables (including query_log) if they don't exist yet."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def _log_query(
    question: str,
    generated_sql: str,
    latency_ms: int,
    tables_used: list[str],
    error: str | None,
) -> None:
    """Persist a query execution record to the query_log table."""
    try:
        _ensure_schema_exists()
        with get_session() as session:
            log_entry = QueryLog(
                question=question,
                generated_sql=generated_sql,
                latency_ms=latency_ms,
                tables_used=",".join(tables_used),
                error=error,
                created_at=datetime.utcnow(),
            )
            session.add(log_entry)
            session.commit()
    except Exception as exc:
        logger.error("Failed to write to query_log: %s", exc)


def _execute_sql(sql: str) -> list[dict[str, Any]]:
    """Run a SQL query and return results as a list of dicts.

    Only single-statement SELECT or WITH (CTE) queries are permitted.
    Any other statement type, or a multi-statement payload, raises ValueError
    so callers receive a clear error instead of executing unexpected SQL.

    A LIMIT clause is injected for SELECT queries so that the response stays
    manageable.
    """
    _MAX_ROWS = 1000
    normalised = sql.strip()

    # Reject multi-statement payloads: strip one trailing semicolon then check
    # for any remaining semicolons which would indicate a second statement.
    if ";" in normalised.rstrip(";"):
        raise ValueError("Multi-statement SQL is not allowed")

    # Allowlist: only SELECT and WITH (CTEs that start WITH … SELECT) are safe
    # read-only operations.  Everything else (PRAGMA, ATTACH, INSERT, …) is
    # rejected here regardless of what upstream guards may have passed.
    first_token = normalised.split()[0].upper() if normalised.split() else ""
    if first_token not in {"SELECT", "WITH"}:
        raise ValueError(
            f"Only SELECT/WITH queries are permitted; got: {first_token!r}"
        )

    normalised_upper = normalised.upper()
    if first_token == "SELECT" and "LIMIT" not in normalised_upper:
        sql = normalised.rstrip(";").rstrip() + f" LIMIT {_MAX_ROWS}"
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]


async def run_query(question: str) -> dict[str, Any]:
    """
    Full LCEL pipeline: natural-language question → SQL → executed results.

    Returns:
        {
            "sql": str,
            "results": list[dict],
            "tables_used": list[str],
            "requires_approval": bool,
            "latency_ms": int,
        }
    """
    start_time = time.monotonic()
    generated_sql = ""
    tables_used: list[str] = []
    error_msg: str | None = None

    try:
        # Step 1: Retrieve relevant schema snippets via RAG
        schema_context = get_relevant_schema(question, k=3)

        # Step 2: Load few-shot examples
        few_shot = _load_few_shot_examples()

        # Step 3: Build prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT),
            ]
        )

        # Step 4: Get cached LLM instance (temperature=0 for deterministic SQL)
        llm = _get_llm()

        # Step 5: Build LCEL chain: prompt | llm | str parser
        chain = prompt | llm | StrOutputParser()

        raw_response: str = await chain.ainvoke(
            {
                "schema": schema_context,
                "examples": few_shot,
                "question": question,
            }
        )

        generated_sql = _extract_sql(raw_response)
        tables_used = _extract_table_names(generated_sql)

        # Step 6: HITL safety check
        guard_result = check_sql(generated_sql)
        latency_ms = int((time.monotonic() - start_time) * 1000)

        if guard_result["requires_approval"]:
            _log_query(question, generated_sql, latency_ms, tables_used, error=None)
            return {
                "sql": generated_sql,
                "results": [],
                "tables_used": tables_used,
                "requires_approval": True,
                "approval_reason": guard_result.get("reason", ""),
                "latency_ms": latency_ms,
            }

        # Step 7: Execute the SQL
        results = await asyncio.to_thread(_execute_sql, generated_sql)
        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Step 8: Log to query_log
        _log_query(question, generated_sql, latency_ms, tables_used, error=None)

        return {
            "sql": generated_sql,
            "results": results,
            "tables_used": tables_used,
            "requires_approval": False,
            "latency_ms": latency_ms,
        }

    except Exception as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        error_msg = str(exc)
        logger.error("run_query failed: %s", exc, exc_info=True)
        _log_query(question, generated_sql, latency_ms, tables_used, error=error_msg)
        raise
