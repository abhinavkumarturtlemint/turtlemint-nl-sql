"""Intent Agent — classifies the question into a business domain.

The domain narrows the search space (QueryGPT "workspaces" idea). Degrades to an
empty intent on failure; the pipeline still proceeds with retrieved tables.
"""
from __future__ import annotations

from typing import Dict

from app.backend import llm
from app.backend.schema_catalog import DOMAINS

_SYSTEM = """You classify a business data question into exactly one domain from \
this list: {domains}. Return ONLY JSON: {{"intent": "<one domain>", \
"confidence": <0..1>}}."""


def classify(question: str) -> Dict:
    try:
        data = llm.chat_json([
            {"role": "system", "content": _SYSTEM.format(domains=", ".join(DOMAINS))},
            {"role": "user", "content": question},
        ])
        intent = (data.get("intent") or "").strip()
        if intent not in DOMAINS:
            intent = next((d for d in DOMAINS if d.lower() in intent.lower()), intent)
        return {"intent": intent, "confidence": float(data.get("confidence", 0) or 0)}
    except (llm.LLMError, ValueError, TypeError):
        return {"intent": "", "confidence": 0.0}
