"""
api/routes/health.py — /api/health liveness and readiness check.
"""

import logging
import os
import time
from typing import Any

import chromadb
from fastapi import APIRouter
from sqlalchemy import text

from model.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])

# Cache the OpenAI key-presence result so we don't hit the API (or even do
# expensive instantiation) on every health-check request.
_openai_check_cache: dict[str, Any] = {}
_OPENAI_CACHE_TTL = 60  # seconds


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Check connectivity for:
    - Database (SQLite or PostgreSQL via SQLAlchemy)
    - ChromaDB vector store
    - OpenAI API key presence (cached for 60 s to avoid per-request API calls)
    """
    status: dict[str, Any] = {
        "status": "ok",
        "checks": {},
    }

    # --- Database check ---
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["checks"]["database"] = "ok"
    except Exception as exc:
        status["checks"]["database"] = f"error: {exc}"
        status["status"] = "degraded"

    # --- ChromaDB check ---
    try:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
        client = chromadb.PersistentClient(path=persist_dir)
        collections = client.list_collections()
        status["checks"]["chromadb"] = f"ok ({len(collections)} collection(s))"
    except Exception as exc:
        status["checks"]["chromadb"] = f"error: {exc}"
        status["status"] = "degraded"

    # --- OpenAI check (key presence only, cached) ---
    now = time.monotonic()
    if _openai_check_cache.get("expires_at", 0) > now:
        status["checks"]["openai"] = _openai_check_cache["result"]
        if _openai_check_cache.get("degraded"):
            status["status"] = "degraded"
    else:
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            openai_result = "ok (key present)"
            degraded = False
        except Exception as exc:
            openai_result = f"error: {exc}"
            degraded = True

        status["checks"]["openai"] = openai_result
        if degraded:
            status["status"] = "degraded"

        _openai_check_cache["result"] = openai_result
        _openai_check_cache["degraded"] = degraded
        _openai_check_cache["expires_at"] = now + _OPENAI_CACHE_TTL

    return status
