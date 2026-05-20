"""Orchestrator for the full agentic pipeline (QueryGPT pattern).

Three phases, matching the human-in-the-loop UX:

  plan(question)         Prompt Enhancer -> retrieve (vector index) -> Intent
                         Agent -> Table Agent. Returns tables for the user to
                         CONFIRM. No SQL yet.

  build_sql(q, tables)   Column Prune -> live schema (catalog) -> SQL Generator
                         -> Guardrails. Returns previewable SQL.

  format_result(...)     Result Formatter -> plain-English summary + chart hint.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.backend import guardrails, knowledge, sql_generator
from app.backend.agents import (column_prune, intent_agent, prompt_enhancer,
                                result_formatter, table_agent)
from app.backend.schema_catalog import schema_prompt_for, table_names


@dataclass
class Plan:
    question: str
    enhanced_question: str
    intent: str
    confidence: float
    candidate_tables: List[str]
    selected_tables: List[str]
    reason: str
    used_embeddings: bool
    all_tables: List[str] = field(default_factory=table_names)


def plan(question: str, previous: Optional[str] = None) -> Plan:
    enhanced = prompt_enhancer.enhance(question, previous)
    retr = knowledge.retrieve(enhanced)
    intent = intent_agent.classify(enhanced)
    tbl = table_agent.select(enhanced, retr.tables)
    return Plan(
        question=question,
        enhanced_question=enhanced,
        intent=intent["intent"],
        confidence=intent["confidence"],
        candidate_tables=retr.tables,
        selected_tables=tbl["tables"],
        reason=tbl["reason"],
        used_embeddings=retr.used_embeddings,
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


def build_sql(question: str, tables: List[str], previous: Optional[str] = None) -> SqlPlan:
    pruned = column_prune.prune(question, tables)
    schema_text = schema_prompt_for(tables, pruned)
    retr = knowledge.retrieve(question)
    examples_text = knowledge.examples_block(retr.examples)

    gen = sql_generator.generate_with(question, schema_text, examples_text, previous)
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
    )


def format_result(question: str, columns: List[str], rows: List[List[Any]]) -> Dict:
    return result_formatter.summarize(question, columns, rows)
