"""Runs validated SELECT SQL and returns columns + rows.

Two backends, chosen by config.DB_BACKEND:
  * "chdb"            -> embedded ClickHouse (dummy-data phase, no server).
  * "clickhouse_http" -> a real ClickHouse HTTP endpoint via a read-only user
                          (the production path; swap in by changing .env).

Both speak ClickHouse SQL, so the generated SQL is identical across phases.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Optional

from app.backend import config


class ExecutorError(RuntimeError):
    pass


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


def _settings_clause() -> str:
    # Timeout + a generous hard row backstop (the SQL LIMIT is the main control).
    return (f" SETTINGS max_execution_time={config.QUERY_TIMEOUT_S}, "
            f"max_result_rows=100000, result_overflow_mode='break'")


# --- chdb (embedded ClickHouse) -------------------------------------------
_session = None


def _get_session():
    global _session
    if _session is None:
        from chdb import session as chs
        config.ensure_dirs()
        _session = chs.Session(config.CHDB_PATH)
    return _session


def _run_chdb(sql: str) -> QueryResult:
    sess = _get_session()
    try:
        raw = sess.query(sql + _settings_clause(), "JSON")
    except Exception as e:
        raise ExecutorError(str(e)) from e
    text = str(raw).strip()
    if not text:
        return QueryResult([], [], 0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ExecutorError(f"Could not parse database output: {e}") from e
    columns = [m["name"] for m in data.get("meta", [])]
    rows = [[row.get(c) for c in columns] for row in data.get("data", [])]
    return QueryResult(columns, rows, data.get("rows", len(rows)))


# --- real ClickHouse over HTTP --------------------------------------------
_ch_client = None


def _get_ch_client():
    global _ch_client
    if _ch_client is None:
        import clickhouse_connect
        if not config.CLICKHOUSE_URL:
            raise ExecutorError("CLICKHOUSE_URL is not set for clickhouse_http backend.")
        _ch_client = clickhouse_connect.get_client(
            dsn=config.CLICKHOUSE_URL,
            username=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD,
            connect_timeout=10,
            query_limit=0,
        )
    return _ch_client


def _run_clickhouse_http(sql: str) -> QueryResult:
    client = _get_ch_client()
    try:
        result = client.query(sql, settings={"max_execution_time": config.QUERY_TIMEOUT_S})
    except Exception as e:
        raise ExecutorError(str(e)) from e
    columns = list(result.column_names)
    rows = [list(r) for r in result.result_rows]
    return QueryResult(columns, rows, len(rows))


def run(sql: str) -> QueryResult:
    if config.DB_BACKEND == "chdb":
        return _run_chdb(sql)
    if config.DB_BACKEND == "clickhouse_http":
        return _run_clickhouse_http(sql)
    raise ExecutorError(f"Unknown DB_BACKEND: {config.DB_BACKEND}")
