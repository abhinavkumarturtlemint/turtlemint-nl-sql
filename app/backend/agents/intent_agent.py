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
"confidence": <0..1>}}.

Domain guide:
- Partners       → insurance advisors / POSP / DP / agents signing up
- Customers      → insurance policy holders / proposer / insured person
- Policies       → insurance policy count, premium, renewals, lapse, sum assured
- Claims         → insurance claims filed, settled, pending
- Commissions    → partner commissions / earnings
- Loans          → personal loans, loan customers, loan leads, sachet lending, funnel stages, CRIF, credit score, loan amount, EMI, ROI, pre-approval, rejection reason, user quality
- LoanOffers     → lender offers, offer comparison, offer ROI, offer EMI, offer status, GRID/IHUB route, processing fee, rejected offers
- LoanLeads      → loan lead volume, lead quality, lead stage, partner loan leads, broker/tenant platform

When the question mentions "offer", "lender", "EMI", "ROI", "loan", "credit score", "failed to get a loan", "did not receive an offer", "personal loan", or "sachet" — always choose Loans, LoanOffers, or LoanLeads (never Customers or Policies)."""


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
