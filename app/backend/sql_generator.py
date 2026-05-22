"""SQL Generator — the single LLM call that turns a question into SQL.

This is the "spine" generator (SOW Phase 1): the full schema for a small set of
tables is passed in-prompt, along with business definitions and a few golden
example pairs. Returns the SQL plus a plain-English explanation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.backend import llm
from app.backend.schema_catalog import example_block, schema_prompt

_SYSTEM = """You are an expert data analyst for Turtlemint, an Indian insurance \
marketplace. You translate a business user's plain-English question into a single \
ClickHouse SQL SELECT query.

Hard rules:
- Output ONLY a JSON object: {"sql": "...", "explanation": "..."}.
- The SQL must be a single read-only SELECT statement. Never write INSERT, UPDATE, \
DELETE, DROP, ALTER or any statement that changes data.
- Use ONLY the tables and columns given in the schema. Never invent names.
- Always qualify tables with the database, e.g. turtlemint.policy.
- Use valid ClickHouse syntax and functions (e.g. toStartOfMonth, addMonths, now()).
- Apply the business definitions provided.
- "explanation" is one or two plain-English sentences a non-technical user can \
understand. Do not mention SQL keywords in it.
- If the question cannot be answered from the schema, return a best-effort SELECT \
and explain the limitation in "explanation".

CRITICAL — Name / person lookups in policydetail:
A person's name can appear in MULTIPLE columns depending on their role. \
You MUST search ALL relevant name columns using OR so you never miss a match:
  • Partner / agent / DP / intermediary → salesdetail_intermediaryname  (full name, one field)
  • Customer / proposer / insured       → proposer_fname AND proposer_lname (two separate fields)
  • Area Manager                        → salesdetail_am
  • Relationship Manager (RM)           → salesdetail_rm
  • Sales Manager (SM)                  → salesdetail_sm
When the role is unknown, ALWAYS combine with OR:
  WHERE lower(salesdetail_intermediaryname) ILIKE '%full name%'
     OR (lower(proposer_fname) ILIKE '%first%' AND lower(proposer_lname) ILIKE '%last%')
Do NOT search only proposer_fname/proposer_lname — that will miss partners and agents."""


@dataclass
class GenResult:
    sql: str
    explanation: str


def generate(question: str) -> GenResult:
    """Spine generator: full catalog in-prompt (used by tests / fallback)."""
    return generate_with(question, schema_prompt(), example_block())


def generate_with(question: str, schema_text: str, examples_text: str,
                  previous: Optional[str] = None) -> GenResult:
    """Agentic generator: receives the pruned schema for the confirmed tables
    plus the retrieved few-shot examples. `previous` carries a prior question
    for in-thread refinement."""
    parts = [
        schema_text,
        f"\nSemantic context (metric definitions, business terms, example queries):\n{examples_text}"
        if examples_text else "",
    ]
    if previous:
        parts.append(f"\nThis is a refinement of an earlier question: {previous}")
    parts.append(f"\nNow write the SQL for this question:\n{question}")
    data = llm.chat_json([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": "\n".join(p for p in parts if p)},
    ])
    sql = (data.get("sql") or "").strip()
    explanation = (data.get("explanation") or "").strip()
    if not sql:
        raise llm.LLMError("The model did not return any SQL.")
    return GenResult(sql=sql, explanation=explanation)
