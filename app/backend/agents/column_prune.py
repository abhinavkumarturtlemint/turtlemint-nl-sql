"""Column Prune Agent — drops columns irrelevant to the question.

Reduces tokens and noise before SQL generation (matters at real schema scale).
Returns {table: [keep_columns]}. On failure (or if it would prune everything)
it returns {} = keep all columns.
"""
from __future__ import annotations

from typing import Dict, List

from app.backend import llm
from app.backend.schema_catalog import get_table

_SYSTEM = """You keep only the columns relevant to answering a question. For each \
table, list the columns to KEEP (always keep id/join keys and any column used for \
filtering, grouping, or aggregation). Return ONLY JSON mapping table name to a \
list of column names, e.g. {"policy": ["policy_id", "premium", "product_type"]}."""


def _schema_block(tables: List[str]) -> str:
    out = []
    for name in tables:
        t = get_table(name)
        if not t:
            continue
        cols = ", ".join(c["name"] for c in t["columns"])
        out.append(f"{name} ({t['description']}): {cols}")
    return "\n".join(out)


def prune(question: str, tables: List[str]) -> Dict[str, List[str]]:
    try:
        data = llm.chat_json([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content":
                f"Question: {question}\n\nTables and columns:\n{_schema_block(tables)}"},
        ])
    except llm.LLMError:
        return {}

    pruned: Dict[str, List[str]] = {}
    for name in tables:
        t = get_table(name)
        if not t:
            continue
        valid = {c["name"] for c in t["columns"]}
        keep = [c for c in (data.get(name) or []) if c in valid]
        if keep:
            pruned[name] = keep
    return pruned
