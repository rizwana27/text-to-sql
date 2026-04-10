#!/usr/bin/env python3
"""
build_index.py — One-time script to embed the semantic schema into ChromaDB.

Run this once after setting up your environment:
    python -m agent.build_index

# INTERN NOTE: RAG indexing explained
# We can't stuff the entire database schema into every LLM prompt — it would
# exceed the context window and add noise. Instead we pre-embed each table's
# schema (name + description + column descriptions) into a vector store.
# At query time, we embed the user's question and do a similarity search to
# retrieve only the 2-3 most relevant tables. This is Retrieval-Augmented
# Generation (RAG): retrieve → augment prompt → generate SQL.
# The vectors are persisted to disk so we don't re-embed on every restart.
"""

import os
import logging
from dotenv import load_dotenv
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from agent.semantic_layer import SEMANTIC_SCHEMA

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

COLLECTION_NAME = "schema_index"


def serialize_table(table: dict) -> str:
    """Serialize a single table entry from SEMANTIC_SCHEMA to a plain-text string."""
    lines = [
        f"Table: {table['table_name']}",
        f"Description: {table['description']}",
        "Columns:",
    ]
    for col in table["columns"]:
        lines.append(f"  - {col['name']}: {col['description']}")
    return "\n".join(lines)


def build_index() -> None:
    """Embed every table in SEMANTIC_SCHEMA and persist vectors to ChromaDB."""
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set. Cannot create embeddings.")

    logger.info("Initializing ChromaDB client at %s", persist_dir)
    client = chromadb.PersistentClient(path=persist_dir)

    embedding_fn = OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name=embedding_model,
    )

    # Delete existing collection to allow clean re-indexing
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing collection '%s'", COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for table in SEMANTIC_SCHEMA:
        text = serialize_table(table)
        documents.append(text)
        metadatas.append({"table_name": table["table_name"]})
        ids.append(table["table_name"])
        logger.info("Prepared embedding for table: %s", table["table_name"])

    logger.info("Upserting %d documents into ChromaDB...", len(documents))
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    logger.info("Index build complete. %d tables indexed.", len(documents))


if __name__ == "__main__":
    build_index()
