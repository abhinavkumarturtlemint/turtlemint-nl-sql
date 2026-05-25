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
- Insurance policies, claims, commissions → policydetail (or policy/claim/commission)
- Insurance advisors/agents/POSP/DP → partner table (ONLY when question explicitly says partner/agent/advisor/POSP/DP)
- Loan / lending / personal-loan customers, loan leads, lenders, ROI, EMI, credit score → leadorderinfo or loanoffers
- "What is email/phone/contact of [person name]" with NO mention of partner/agent/insurance → leadorderinfo (loan customers have email in leadcustomerinfo_email)
- "Find all information about [name]" or "customer name [name]" with no other context → ALWAYS include leadorderinfo alongside policydetail.
- NEVER select only 'partner' for a generic person-name lookup — loan customers are in leadorderinfo, not partner."""


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
