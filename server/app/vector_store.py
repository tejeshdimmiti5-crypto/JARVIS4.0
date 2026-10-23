from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from typing import Any

import httpx
from qdrant_client import QdrantClient, models

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "").strip()
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "jarvis_documents").strip() or "jarvis_documents"

_client = (
    QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=15.0)
    if QDRANT_URL and QDRANT_API_KEY
    else None
)


async def embed(text: str) -> list[float]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for semantic indexing")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"
    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text}]},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": GEMINI_API_KEY},
                    json=payload,
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                if attempt == 2:
                    raise RuntimeError("Embedding provider connection failed") from exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                await asyncio.sleep(min(1.5 * (attempt + 1), 5))
                continue
            break
    if response.status_code >= 400:
        raise RuntimeError("Embedding provider request failed")
    try:
        return response.json()["embedding"]["values"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Embedding provider returned an invalid response") from exc


def _ensure_collection(vector_size: int) -> None:
    if _client is None:
        return
    if not _client.collection_exists(QDRANT_COLLECTION):
        _client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )


async def index_chunks(document_id: str, chunks: list[dict[str, Any]]) -> int:
    # Vector search is optional until QDRANT_URL and QDRANT_API_KEY are configured.
    # Text extraction and lexical retrieval still work without a vector service.
    if _client is None or not chunks:
        return 0

    points = []
    for index, chunk in enumerate(chunks):
        text = chunk["text"].strip()
        if not text:
            continue
        vector = await embed(text)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{index}"))
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "document_id": document_id,
                    "page": int(chunk.get("page", 1)),
                    "chunk": index,
                    "text": text,
                    "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                },
            )
        )

    if not points:
        return 0
    _ensure_collection(len(points[0].vector))
    _client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
    return len(points)


async def semantic_search(
    query: str,
    document_id: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    query = query.strip()
    if not query or top_k <= 0 or _client is None:
        return []
    if not _client.collection_exists(QDRANT_COLLECTION):
        return []

    vector = await embed(query)
    query_filter = None
    if document_id:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )
    result = _client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        query_filter=query_filter,
        limit=max(1, min(top_k, 20)),
        with_payload=True,
    )
    matches = []
    for point in result.points:
        payload = point.payload or {}
        matches.append(
            {
                "text": str(payload.get("text", "")),
                "page": int(payload.get("page", 1)),
                "document_id": payload.get("document_id"),
                "distance": 1.0 - float(point.score),
            }
        )
    return matches


def vector_store_status() -> str:
    return "qdrant" if _client is not None else "not_configured"
