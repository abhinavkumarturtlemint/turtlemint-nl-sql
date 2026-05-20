"""Spine + agentic-endpoint tests. The real chdb executor runs against an
isolated, seeded store (see conftest); LLM-using stages are monkeypatched so
these run without an API key.
"""
from app.backend import executor, llm, pipeline, sql_generator
from app.backend import main as backend
from app.backend.main import GenerateRequest, RunRequest


def test_executor_returns_rows():
    res = executor.run("SELECT status, count(*) AS c FROM turtlemint.partner GROUP BY status")
    assert res.columns[0] == "status"
    assert res.row_count >= 1


def test_generate_uses_llm(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {
        "sql": "SELECT count(*) AS partners FROM turtlemint.partner",
        "explanation": "Counts all partners.",
    })
    gen = sql_generator.generate("how many partners are there?")
    assert "SELECT" in gen.sql.upper()
    assert gen.explanation


def test_generate_endpoint(monkeypatch):
    monkeypatch.setattr(pipeline, "build_sql", lambda q, t, prev=None: pipeline.SqlPlan(
        sql="SELECT count(*) AS partners FROM turtlemint.partner LIMIT 1000",
        raw_sql="SELECT count(*) AS partners FROM turtlemint.partner",
        explanation="Counts all partners.", tables=t, pruned_columns={},
        limit_applied=True, guardrail_ok=True, guardrail_error=None,
    ))
    resp = backend.generate_endpoint(GenerateRequest(question="how many partners?",
                                                     tables=["partner"]))
    assert resp.ok and resp.guardrail_ok
    assert "LIMIT" in resp.sql.upper()


def test_run_endpoint_executes(monkeypatch):
    monkeypatch.setattr(pipeline, "format_result",
                        lambda *a, **k: {"summary": "", "chart": None})
    resp = backend.run_endpoint(RunRequest(
        sql="SELECT product_type, count(*) AS c FROM turtlemint.policy GROUP BY product_type",
        question="policies by product"))
    assert resp.ok
    assert resp.row_count >= 1
    assert "product_type" in resp.columns


def test_run_endpoint_blocks_destructive():
    resp = backend.run_endpoint(RunRequest(sql="DROP TABLE turtlemint.partner",
                                           question="drop it"))
    assert not resp.ok
    assert "guardrail" in (resp.error or "").lower()
