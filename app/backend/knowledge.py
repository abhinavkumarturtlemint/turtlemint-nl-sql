"""RAG knowledge layer — the lightweight semantic index from the SOW.

Indexes table summaries and example Q->SQL pairs with Gemini embeddings, then
retrieves the most relevant tables + examples for a question (cosine similarity).

This is the "vector index for discovery" half of the hybrid schema strategy.
The full schema for SQL generation is still fetched per-table from the catalog
(schema_catalog.schema_prompt_for) — the stand-in for a live OpenMetadata call.

At our dummy scale (5 tables) the index is small; the value is architectural —
it scales to hundreds of tables and swaps to Chroma/pgvector without changing
callers. If embeddings are unavailable, retrieval falls back to "all tables".
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from app.backend import config, embeddings
from app.backend.schema_catalog import CATALOG, table_doc

_META_PATH = config.INDEX_PATH + ".meta.json"


@dataclass
class Retrieval:
    tables: List[str]
    examples: List[Dict[str, str]]
    used_embeddings: bool


def build_index() -> bool:
    """Embed all docs and persist the index. Returns True if embeddings worked."""
    config.ensure_dirs()
    docs, meta = [], []
    for t in CATALOG["tables"]:
        docs.append(table_doc(t))
        meta.append({"type": "table", "name": t["name"]})
    for ex in CATALOG["example_queries"]:
        docs.append(ex["question"])
        meta.append({"type": "example", "question": ex["question"], "sql": ex["sql"]})

    vecs = embeddings.embed(docs)
    if vecs is None:
        return False
    arr = np.array(vecs, dtype=np.float32)
    arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)
    np.savez(config.INDEX_PATH, vectors=arr)
    with open(_META_PATH, "w") as f:
        json.dump(meta, f)
    return True


def _load() -> Optional[tuple]:
    if not (os.path.exists(config.INDEX_PATH) and os.path.exists(_META_PATH)):
        return None
    try:
        arr = np.load(config.INDEX_PATH)["vectors"]
        with open(_META_PATH) as f:
            meta = json.load(f)
        return arr, meta
    except Exception:
        return None


def _all_tables_fallback() -> Retrieval:
    return Retrieval(
        tables=[t["name"] for t in CATALOG["tables"]],
        examples=[{"question": e["question"], "sql": e["sql"]}
                  for e in CATALOG["example_queries"]],
        used_embeddings=False,
    )


def retrieve(question: str, k_tables: int = 4, k_examples: int = 3) -> Retrieval:
    loaded = _load()
    if loaded is None:
        if not build_index():
            return _all_tables_fallback()
        loaded = _load()
        if loaded is None:
            return _all_tables_fallback()

    arr, meta = loaded
    qv = embeddings.embed_one(question)
    if qv is None:
        return _all_tables_fallback()
    q = np.array(qv, dtype=np.float32)
    q /= (np.linalg.norm(q) + 1e-9)
    sims = arr @ q

    order = np.argsort(-sims)
    tables, examples = [], []
    for i in order:
        m = meta[int(i)]
        if m["type"] == "table" and len(tables) < k_tables:
            tables.append(m["name"])
        elif m["type"] == "example" and len(examples) < k_examples:
            examples.append({"question": m["question"], "sql": m["sql"]})
        if len(tables) >= k_tables and len(examples) >= k_examples:
            break
    if not tables:  # safety
        return _all_tables_fallback()
    return Retrieval(tables=tables, examples=examples, used_embeddings=True)


def examples_block(examples: List[Dict[str, str]]) -> str:
    return "\n\n".join(f"Q: {e['question']}\nSQL: {e['sql']}" for e in examples)
