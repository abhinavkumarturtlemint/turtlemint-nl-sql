"""Audit log — one row per executed question, in a local SQLite file.

Also provides the helpers used for Phase 4 hardening: recent activity (admin
view) and a per-user daily count (rate limiting).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.backend import config

_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    user_id       TEXT,
    question      TEXT,
    intent        TEXT,
    tables        TEXT,
    generated_sql TEXT,
    executed_sql  TEXT,
    success       INTEGER,
    row_count     INTEGER,
    error         TEXT,
    latency_ms    INTEGER,
    model         TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    llm_calls     INTEGER DEFAULT 0
)
"""

# Columns added after the original Phase 1 schema; migrate existing DBs in place.
_MIGRATIONS = [
    ("intent", "TEXT"), ("tables", "TEXT"), ("prompt_tokens", "INTEGER DEFAULT 0"),
    ("completion_tokens", "INTEGER DEFAULT 0"), ("llm_calls", "INTEGER DEFAULT 0"),
]


def _connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.AUDIT_DB_PATH)
    conn.execute(_DDL)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)")}
    for col, decl in _MIGRATIONS:
        if col not in existing:
            conn.execute(f"ALTER TABLE audit_log ADD COLUMN {col} {decl}")
    conn.commit()
    return conn


def log(*, user_id: str, question: str, intent: str = "", tables: str = "",
        generated_sql: str = "", executed_sql: str = "", success: bool = False,
        row_count: int = 0, error: Optional[str] = None, latency_ms: int = 0,
        model: str = "", prompt_tokens: int = 0, completion_tokens: int = 0,
        llm_calls: int = 0) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO audit_log (ts, user_id, question, intent, tables, "
            "generated_sql, executed_sql, success, row_count, error, latency_ms, "
            "model, prompt_tokens, completion_tokens, llm_calls) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), user_id, question, intent, tables,
             generated_sql, executed_sql, 1 if success else 0, row_count, error,
             latency_ms, model, prompt_tokens, completion_tokens, llm_calls),
        )
        conn.commit()
    finally:
        conn.close()


def recent(limit: int = 20, user_id: Optional[str] = None) -> List[Dict]:
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        sql = ("SELECT ts, user_id, question, intent, tables, success, row_count, "
               "latency_ms, error, prompt_tokens, completion_tokens, llm_calls "
               "FROM audit_log")
        params: tuple = ()
        if user_id:
            sql += " WHERE user_id = ?"
            params = (user_id,)
        sql += " ORDER BY id DESC LIMIT ?"
        params += (limit,)
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def count_today(user_id: str) -> int:
    conn = _connect()
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        row = conn.execute(
            "SELECT count(*) FROM audit_log WHERE user_id = ? AND substr(ts,1,10) = ? "
            "AND success = 1", (user_id, today)).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()
