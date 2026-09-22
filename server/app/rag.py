from __future__ import annotations

import re
from dataclasses import dataclass

@dataclass
class Chunk:
    page: int
    text: str


def chunk_document(text: str, max_chars: int = 1800, overlap: int = 250) -> list[Chunk]:
    if max_chars <= 0 or overlap < 0 or overlap >= max_chars:
        raise ValueError('overlap must be non-negative and smaller than max_chars')
    """Split extracted PDF text into page-aware overlapping chunks."""
    pages = re.split(r"(?=PAGE\s+\d+\n)", text.strip())
    chunks: list[Chunk] = []
    for raw in pages:
        raw = raw.strip()
        if not raw:
            continue
        match = re.match(r"PAGE\s+(\d+)\n", raw)
        page = int(match.group(1)) if match else 1
        body = raw[match.end():] if match else raw
        start = 0
        while start < len(body):
            end = min(start + max_chars, len(body))
            piece = body[start:end].strip()
            if piece:
                chunks.append(Chunk(page=page, text=piece))
            if end >= len(body):
                break
            start = max(end - overlap, start + 1)
    return chunks


def lexical_retrieve(query: str, chunks: list[Chunk], top_k: int = 5) -> list[Chunk]:
    """Small dependency-free retrieval layer; can be replaced by embeddings later."""
    terms = {t for t in re.findall(r"[a-zA-Z0-9]{3,}", query.lower())}
    if not terms or not chunks or top_k <= 0:
        return []
    scored = []
    for chunk in chunks:
        words = set(re.findall(r"[a-zA-Z0-9]{3,}", chunk.text.lower()))
        overlap = len(terms & words)
        if overlap:
            density = overlap / max(len(terms), 1)
            scored.append((density, overlap, -chunk.page, chunk))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [chunk for _, _, _, chunk in scored[:top_k]]
