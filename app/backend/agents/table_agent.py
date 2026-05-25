"""Table Agent — picks the minimal set of tables needed to answer the question.

Chooses from the candidate tables surfaced by the vector index. The result is
shown to the user to CONFIRM before SQL is generated (human-in-the-loop).
Degrades to the full candidate list on failure.
"""
from __future__ import annotations

from typing import Dict, List

from app.backend import llm
from app.backend.schema_catalog import get_table, table_names

_SYSTEM = """You select the minimal set of database tables needed to answer a \
question. Choose only from the candidate tables provided. Prefer the fewest \
tables that fully answer it. Return ONLY JSON: {"tables": ["..."], \
"reason": "one short sentence"}.

Key data source rules — use these to pick the right table:
- Insurance policies, partners, agents, claims, commissions → policydetail (or policy/partner/claim/commission)
- Loan / lending / personal-loan customers, loan leads, lenders, ROI, EMI, credit score → leadorderinfo or loanoffers
- When looking up a person by name and it is UNCLEAR whether they are an insurance customer or a loan customer → include BOTH policydetail AND leadorderinfo as candidates so both are searched.
- "Find all information about [name]" or "customer name [name]" with no other context → ALWAYS include leadorderinfo alongside policydetail."""


def _candidates_block(candidates: List[str]) -> str:
    lines = []
    for name in candidates:
        t = get_table(name)
        if t:
            lines.append(f"- {name}: {t['description']}")
    return "\n".join(lines)


def select(question: str, candidates: List[str]) -> Dict:
    valid = set(table_names())
    try:
        data = llm.chat_json([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content":
                f"Question: {question}\n\nCandidate tables:\n{_candidates_block(candidates)}"},
        ])
        tables = [t for t in (data.get("tables") or []) if t in valid]
        if not tables:
            tables = candidates
        return {"tables": tables, "reason": (data.get("reason") or "").strip()}
    except llm.LLMError:
        return {"tables": candidates, "reason": ""}
