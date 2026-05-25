"""Orchestrator for the full agentic pipeline.

New architecture (live API):

  plan(question)      Prompt Enhancer
                      → Semantic Layer (keyword routing, zero embeddings)
                      → Intent Agent
                      → Table Agent
                      Returns confirmed tables. No SQL yet.

  build_sql(q, tables)
                      ┌── For REAL tables (in openmetadata.TABLE_FQN_MAP):
                      │     Call Turtlemint OpenMetadata API live
                      │     → get context_string (schema + sample rows)
                      │
                      └── For DUMMY/fallback tables:
                            Use hardcoded schema_catalog
                      │
                      ├── Column Prune Agent (dummy tables only)
                      ├── Semantic context (business terms, examples)
                      └── SQL Generator → Guardrails

  format_result(...)  Result Formatter → plain-English summary + chart hint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.backend import executor, glossary, guardrails, openmetadata, semantics, sql_generator
from app.backend.agents import (column_prune, intent_agent, prompt_enhancer,
                                result_formatter, table_agent)
from app.backend.schema_catalog import schema_prompt_for, table_names


# All known tables = dummy catalog tables + BSON tables + real OpenMetadata tables
def _all_table_names() -> List[str]:
    return list(dict.fromkeys(
        table_names()
        + list(executor.BSON_TABLE_MAP.keys())
        + openmetadata.known_tables()
    ))


@dataclass
class Plan:
    question: str
    enhanced_question: str
    intent: str
    confidence: float
    candidate_tables: List[str]
    selected_tables: List[str]
    reason: str
    used_embeddings: bool          # always False; kept for API compatibility
    all_tables: List[str] = field(default_factory=_all_table_names)


def plan(question: str, previous: Optional[str] = None) -> Plan:
    enhanced = prompt_enhancer.enhance(question, previous)

    # Semantic layer: keyword-based routing, zero LLM/embedding calls
    candidate_tables = semantics.get_tables(enhanced)

    intent = intent_agent.classify(enhanced)
    tbl = table_agent.select(enhanced, candidate_tables)

    return Plan(
        question=question,
        enhanced_question=enhanced,
        intent=intent["intent"],
        confidence=intent["confidence"],
        candidate_tables=candidate_tables,
        selected_tables=tbl["tables"],
        reason=tbl["reason"],
        used_embeddings=False,
    )


@dataclass
class SqlPlan:
    sql: str
    raw_sql: str
    explanation: str
    tables: List[str]
    pruned_columns: Dict[str, List[str]]
    limit_applied: bool
    guardrail_ok: bool
    guardrail_error: Optional[str]
    schema_source: str             # "live_api" | "catalog" | "mixed"


_BSON_TABLES = openmetadata._BSON_TABLES   # re-use the same set


def build_sql(question: str, tables: List[str], previous: Optional[str] = None) -> SqlPlan:
    # ── Step 1: fetch schema ─────────────────────────────────────────────────
    # BSON tables  → dynamic schema built from the actual data files
    # Real tables  → call OpenMetadata API live (cached 5 min)
    # Dummy tables → use hardcoded schema_catalog
    bson_tables   = [t for t in tables if t.lower() in _BSON_TABLES]
    other_tables  = [t for t in tables if t.lower() not in _BSON_TABLES]

    real_contexts, dummy_tables = openmetadata.schema_prompt_for_real_tables(other_tables)

    schema_parts: List[str] = []

    # BSON schema (dynamic — built from real file, all columns visible to LLM)
    if bson_tables:
        schema_parts.append("=== SACHET LENDING DATA (LOCAL BSON FILES) ===")
        for t in bson_tables:
            ctx = executor.bson_schema_context(t)
            if ctx:
                schema_parts.append(ctx)

    # Live API schema (real OpenMetadata tables)
    if real_contexts:
        schema_parts.append("=== LIVE SCHEMA FROM OPENMETADATA API ===")
        schema_parts.extend(real_contexts)

    # Fallback schema (dummy/catalog tables)
    if dummy_tables:
        pruned = column_prune.prune(question, dummy_tables)
        schema_parts.append("=== CATALOG SCHEMA ===")
        schema_parts.append(schema_prompt_for(dummy_tables, pruned))
    else:
        pruned = {}

    schema_text = "\n\n".join(schema_parts)

    # Determine schema source label for UI / audit
    if bson_tables and not real_contexts and not dummy_tables:
        schema_source = "bson_local"
    elif real_contexts and not dummy_tables and not bson_tables:
        schema_source = "live_api"
    elif real_contexts or bson_tables:
        schema_source = "mixed"
    else:
        schema_source = "catalog"

    # ── Step 2: semantic context ─────────────────────────────────────────────
    # Static semantic layer (YAML metrics + business terms + example SQL)
    context_parts = [semantics.get_context_prompt(question)]

    # Live glossary (OpenMetadata API) — real Turtlemint business definitions
    # with exact SQL routing notes embedded (e.g. "OD → premiumdetails_netodpremium")
    gloss = glossary.get_context(question)
    if gloss:
        context_parts.append(gloss)

    context_text = "\n\n".join(p for p in context_parts if p)

    # ── Step 3: generate SQL ─────────────────────────────────────────────────
    gen = sql_generator.generate_with(question, schema_text, context_text, previous)

    # ── Step 4: guardrails ───────────────────────────────────────────────────
    guard = guardrails.check(gen.sql)

    return SqlPlan(
        sql=guard.sql if guard.ok else "",
        raw_sql=gen.sql,
        explanation=gen.explanation,
        tables=tables,
        pruned_columns=pruned,
        limit_applied=guard.limit_applied,
        guardrail_ok=guard.ok,
        guardrail_error=guard.error,
        schema_source=schema_source,
    )


def format_result(question: str, columns: List[str], rows: List[List[Any]]) -> Dict:
    return result_formatter.summarize(question, columns, rows)
