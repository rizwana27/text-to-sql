"""
api/routes/schema.py — /api/schema endpoint.
"""

from fastapi import APIRouter
from agent.semantic_layer import SEMANTIC_SCHEMA

router = APIRouter(prefix="/api", tags=["schema"])


@router.get("/schema")
async def get_schema() -> list:
    """Return the full semantic schema as JSON."""
    return SEMANTIC_SCHEMA
