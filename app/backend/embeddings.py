"""Gemini text-embeddings client (OpenAI-compatible /embeddings endpoint).

Used by the RAG knowledge layer. Returns None on failure so callers can fall
back gracefully (at small schema scale, "use all tables" is a fine fallback).
"""
from __future__ import annotations

from typing import List, Optional

import requests

from app.backend import config


def embed(texts: List[str]) -> Optional[List[List[float]]]:
    """Embed a batch of texts. Returns a list of vectors, or None on failure."""
    if not config.LLM_API_KEY or not texts:
        return None
    url = f"{config.LLM_BASE_URL.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json={"model": config.EMBED_MODEL, "input": texts},
                             headers=headers, timeout=config.LLM_TIMEOUT_S)
        if resp.status_code != 200:
            return None
        items = resp.json()["data"]
        # Items come back in request order; sort by "index" only if present.
        if all("index" in d for d in items):
            items = sorted(items, key=lambda d: d["index"])
        return [d["embedding"] for d in items]
    except (requests.RequestException, KeyError, ValueError):
        return None


def embed_one(text: str) -> Optional[List[float]]:
    out = embed([text])
    return out[0] if out else None
