"""Result Formatter agent — turns raw rows into a plain-English summary and a
chart suggestion. Only a small sample of rows is sent to the LLM.

Returns {"summary": str, "chart": {"type","x","y"} | None}. Degrades to no
summary on failure.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.backend import config, llm

_SYSTEM = """You explain a query result to a non-technical business user. Given \
the question, the column names, and a sample of rows, write a one or two sentence \
plain-English summary of what the data shows (use concrete numbers). If the result \
suits a simple chart, suggest one. Return ONLY JSON: {"summary": "...", \
"chart": {"type": "bar"|"line", "x": "<col>", "y": "<col>"} or null}."""


def summarize(question: str, columns: List[str], rows: List[List[Any]]) -> Dict:
    if not config.ENABLE_RESULT_FORMATTER or not columns:
        return {"summary": "", "chart": None}
    sample = rows[:20]
    payload = {"question": question, "columns": columns, "rows": sample}
    try:
        data = llm.chat_json([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ])
    except llm.LLMError:
        return {"summary": "", "chart": None}

    chart = data.get("chart")
    if not (isinstance(chart, dict) and chart.get("x") in columns and chart.get("y") in columns):
        chart = None
    return {"summary": (data.get("summary") or "").strip(), "chart": chart}
