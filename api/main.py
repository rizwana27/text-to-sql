"""
api/main.py — FastAPI application factory.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import health, query, schema

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text-to-SQL API",
    description="Natural-language to SQL query engine powered by GPT-4o and ChromaDB.",
    version="1.0.0",
)

# Allow the Vite dev server and production frontend to call the API.
# ALLOWED_ORIGINS env var should be a comma-separated list of trusted origins in
# production (e.g. "https://yourdomain.com"). Defaults to "*" for local dev only.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
_allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,  # Must be False when allow_origins contains "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a consistent JSON error envelope for all unhandled exceptions."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "message": str(exc)},
    )


app.include_router(query.router)
app.include_router(schema.router)
app.include_router(health.router)
