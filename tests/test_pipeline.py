"""Spine + agentic-endpoint tests.
Executor now uses OpenMetadata API + DuckDB in-memory (no chdb, no local storage).
LLM-using stages are monkeypatched so these run without an API key.
"""
from app.backend import executor, llm, pipeline, sql_generator
from app.backend import main as backend
from app.backend.main import GenerateRequest, RunRequest


def test_executor_returns_rows():
    # Uses the real OpenMetadata API — policydetail is a known real table
    res = executor.run(
        "SELECT insurer, count(*) AS c FROM spectrum.policydetail GROUP BY insurer"
    )
    assert "insurer" in res.columns
    assert res.row_count >= 1


def test_generate_uses_llm(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "sql": "SELECT count(*) AS total FROM spectrum.policydetail",
        "explanation": "Counts all policies.",
    })
    gen = sql_generator.generate("how many policies are there?")
    assert "SELECT" in gen.sql.upper()
    assert gen.explanation


def test_generate_endpoint(monkeypatch):
    monkeypatch.setattr(pipeline, "build_sql", lambda q, t, prev=None: pipeline.SqlPlan(
        sql="SELECT count(*) AS total FROM spectrum.policydetail LIMIT 1000",
        raw_sql="SELECT count(*) AS total FROM spectrum.policydetail",
        explanation="Counts all policies.", tables=t, pruned_columns={},
        limit_applied=True, guardrail_ok=True, guardrail_error=None,
        schema_source="live_api",
    ))
    resp = backend.generate_endpoint(GenerateRequest(question="how many policies?",
                                                     tables=["policydetail"]))
    assert resp.ok and resp.guardrail_ok
    assert "LIMIT" in resp.sql.upper()


def test_run_endpoint_executes(monkeypatch):
    monkeypatch.setattr(pipeline, "format_result",
                        lambda *a, **k: {"summary": "", "chart": None})
    resp = backend.run_endpoint(RunRequest(
        sql="SELECT insurer, count(*) AS c FROM spectrum.policydetail GROUP BY insurer",
        question="policies by insurer"))
    assert resp.ok, resp.error
    assert resp.row_count >= 1
    assert "insurer" in resp.columns


def test_run_endpoint_blocks_destructive():
    resp = backend.run_endpoint(RunRequest(sql="DROP TABLE spectrum.policydetail",
                                           question="drop it"))
    assert not resp.ok
    assert "guardrail" in (resp.error or "").lower()
