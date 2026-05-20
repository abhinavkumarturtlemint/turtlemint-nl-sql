"""FastAPI backend — full agentic pipeline (Phases 1–4).

A question flows through three user-visible steps:

  POST /plan      Prompt Enhancer -> retrieve -> Intent -> Table Agent
                  Returns the chosen tables for the user to CONFIRM.
  POST /generate  Column Prune -> live schema -> SQL Generator -> Guardrails
                  Returns previewable SQL (the user reviews before running).
  POST /run       Guardrails (re-checked) -> Executor -> Result Formatter
                  Executes, summarises, and writes the audit log. Rate-limited.

  GET  /audit     Recent activity (admin view).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from app.backend import (audit, config, executor, guardrails, knowledge, llm,
                         pipeline)
from app.backend.schema_catalog import CATALOG, DOMAINS

app = FastAPI(title="Turtlemint NL-SQL (agentic pipeline)")


# --- models ----------------------------------------------------------------
class PlanRequest(BaseModel):
    question: str
    previous: Optional[str] = None
    user_id: str = "demo"


class PlanResponse(BaseModel):
    ok: bool
    enhanced_question: str = ""
    intent: str = ""
    confidence: float = 0.0
    candidate_tables: List[str] = []
    selected_tables: List[str] = []
    all_tables: List[str] = []
    reason: str = ""
    used_embeddings: bool = False
    usage: Dict[str, int] = {}
    error: Optional[str] = None


class GenerateRequest(BaseModel):
    question: str
    tables: List[str]
    previous: Optional[str] = None
    user_id: str = "demo"


class GenerateResponse(BaseModel):
    ok: bool
    sql: str = ""
    raw_sql: str = ""
    explanation: str = ""
    pruned_columns: Dict[str, List[str]] = {}
    limit_applied: bool = False
    guardrail_ok: bool = False
    guardrail_error: Optional[str] = None
    usage: Dict[str, int] = {}
    error: Optional[str] = None


class RunRequest(BaseModel):
    sql: str
    question: str = ""
    intent: str = ""
    tables: List[str] = []
    user_id: str = "demo"


class RunResponse(BaseModel):
    ok: bool
    columns: List[str] = []
    rows: List[List[Any]] = []
    row_count: int = 0
    latency_ms: int = 0
    executed_sql: str = ""
    summary: str = ""
    chart: Optional[Dict[str, str]] = None
    usage: Dict[str, int] = {}
    error: Optional[str] = None


# --- endpoints -------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "db_backend": config.DB_BACKEND,
        "llm_configured": llm.is_configured(),
        "model": config.LLM_MODEL,
        "features": {
            "prompt_enhancer": config.ENABLE_PROMPT_ENHANCER,
            "result_formatter": config.ENABLE_RESULT_FORMATTER,
        },
        "max_queries_per_day": config.MAX_QUERIES_PER_DAY,
    }


@app.get("/schema")
def schema():
    return {"catalog": CATALOG, "domains": DOMAINS, "db_backend": config.DB_BACKEND,
            "llm_configured": llm.is_configured(), "model": config.LLM_MODEL}


@app.post("/plan", response_model=PlanResponse)
def plan_endpoint(req: PlanRequest):
    llm.reset_usage()
    try:
        p = pipeline.plan(req.question, req.previous)
    except llm.LLMError as e:
        return PlanResponse(ok=False, error=str(e), usage=llm.get_usage())
    return PlanResponse(
        ok=True, enhanced_question=p.enhanced_question, intent=p.intent,
        confidence=p.confidence, candidate_tables=p.candidate_tables,
        selected_tables=p.selected_tables, all_tables=p.all_tables,
        reason=p.reason, used_embeddings=p.used_embeddings, usage=llm.get_usage(),
    )


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest):
    llm.reset_usage()
    if not req.tables:
        return GenerateResponse(ok=False, error="No tables selected.")
    try:
        sp = pipeline.build_sql(req.question, req.tables, req.previous)
    except llm.LLMError as e:
        return GenerateResponse(ok=False, error=str(e), usage=llm.get_usage())
    return GenerateResponse(
        ok=True, sql=sp.sql, raw_sql=sp.raw_sql, explanation=sp.explanation,
        pruned_columns=sp.pruned_columns, limit_applied=sp.limit_applied,
        guardrail_ok=sp.guardrail_ok, guardrail_error=sp.guardrail_error,
        usage=llm.get_usage(),
    )


@app.post("/run", response_model=RunResponse)
def run_endpoint(req: RunRequest):
    llm.reset_usage()
    # Rate limit (Phase 4 guardrail).
    if audit.count_today(req.user_id) >= config.MAX_QUERIES_PER_DAY:
        return RunResponse(ok=False, error=(
            f"Daily query limit reached ({config.MAX_QUERIES_PER_DAY}). "
            "Try again tomorrow."))

    # Never trust the client — re-validate before executing.
    guard = guardrails.check(req.sql)
    if not guard.ok:
        audit.log(user_id=req.user_id, question=req.question, intent=req.intent,
                  tables=",".join(req.tables), generated_sql=req.sql, success=False,
                  error=f"guardrail: {guard.error}", model=config.LLM_MODEL)
        return RunResponse(ok=False, error=f"Blocked by guardrails: {guard.error}")

    start = time.perf_counter()
    try:
        result = executor.run(guard.sql)
    except executor.ExecutorError as e:
        latency = int((time.perf_counter() - start) * 1000)
        audit.log(user_id=req.user_id, question=req.question, intent=req.intent,
                  tables=",".join(req.tables), generated_sql=req.sql,
                  executed_sql=guard.sql, success=False, error=str(e),
                  latency_ms=latency, model=config.LLM_MODEL)
        return RunResponse(ok=False, executed_sql=guard.sql, latency_ms=latency, error=str(e))
    latency = int((time.perf_counter() - start) * 1000)

    fmt = pipeline.format_result(req.question, result.columns, result.rows)
    usage = llm.get_usage()
    audit.log(user_id=req.user_id, question=req.question, intent=req.intent,
              tables=",".join(req.tables), generated_sql=req.sql,
              executed_sql=guard.sql, success=True, row_count=result.row_count,
              latency_ms=latency, model=config.LLM_MODEL,
              prompt_tokens=usage["prompt_tokens"],
              completion_tokens=usage["completion_tokens"], llm_calls=usage["calls"])
    return RunResponse(
        ok=True, columns=result.columns, rows=result.rows,
        row_count=result.row_count, latency_ms=latency, executed_sql=guard.sql,
        summary=fmt["summary"], chart=fmt["chart"], usage=usage,
    )


@app.get("/audit")
def audit_endpoint(limit: int = 20, user_id: Optional[str] = None):
    return {"rows": audit.recent(limit=min(limit, 200), user_id=user_id)}
