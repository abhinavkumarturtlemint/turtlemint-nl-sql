"""Prompt Enhancer agent — cleans/clarifies the user's question.

Also folds in a previous question when the user is refining ("no, last month").
Degrades gracefully: on any failure it returns the original question.
"""
from __future__ import annotations

from typing import Optional

from app.backend import config, llm

_SYSTEM = """You rewrite a business user's data question into one clear, \
self-contained analytical question for a text-to-SQL system. Fix typos and \
vagueness. Keep the user's intent and any time ranges. If a PREVIOUS question is \
given, treat the new text as a refinement and merge them into one full question. \
Return ONLY JSON: {"enhanced": "..."}."""


def enhance(question: str, previous: Optional[str] = None) -> str:
    if not config.ENABLE_PROMPT_ENHANCER:
        return question
    user = question if not previous else f"PREVIOUS question: {previous}\nRefinement: {question}"
    try:
        data = llm.chat_json([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ])
        return (data.get("enhanced") or "").strip() or question
    except llm.LLMError:
        return question
