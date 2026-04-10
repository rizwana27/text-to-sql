"""
api/routes/health.py — /api/health liveness and readiness check.
"""

import logging
import os
from typing import Any

import chromadb
from fastapi import APIRouter
from sqlalchemy import text

from model.database import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Check connectivity for:
    - Database (SQLite or PostgreSQL via SQLAlchemy)
    - ChromaDB vector store
    - OpenAI API (lightweight ping)
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

    # --- OpenAI check ---
    try:
        import openai

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        client_oai = openai.OpenAI(api_key=api_key)
        # Minimal, cheap call — list models endpoint
        models = client_oai.models.list()
        gpt4o_available = any("gpt-4o" in m.id for m in models.data)
        status["checks"]["openai"] = f"ok (gpt-4o available: {gpt4o_available})"
    except Exception as exc:
        status["checks"]["openai"] = f"error: {exc}"
        status["status"] = "degraded"

    return status
