"""Deterministic safety layer between the LLM's SQL and the database.

Controls implemented here (the "logical" guardrails from the SOW):
  1. Single statement only (blocks stacked-query injection).
  2. SELECT-only (blocks INSERT/UPDATE/DELETE/DDL/etc).
  3. Auto-append a row LIMIT when the query has none.

Physical controls (read-only DB credential, query timeout, result-row cap) are
enforced at the executor / database layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import sqlglot
from sqlglot import exp

from app.backend import config

# Expression types that must never reach the database.
_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Use, exp.Set,
)
_ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Subquery, exp.With)

# Words that must not appear (defence-in-depth for the regex fallback path).
_FORBIDDEN_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|"
    r"attach|detach|optimize|rename|replace|merge|call|use|set)\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    ok: bool
    sql: str                  # cleaned SQL (with LIMIT) when ok
    error: Optional[str] = None
    limit_applied: bool = False


def _strip(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def check(sql: str) -> GuardResult:
    raw = _strip(sql)
    if not raw:
        return GuardResult(False, "", "Empty query.")

    # Reject obvious multi-statement input early.
    if ";" in raw:
        return GuardResult(False, raw, "Multiple SQL statements are not allowed.")

    try:
        statements = sqlglot.parse(raw, read=config.SQL_DIALECT)
    except Exception:
        return _regex_fallback(raw)

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return GuardResult(False, raw, "Exactly one SELECT statement is required.")

    tree = statements[0]

    # Root must be a read expression.
    if not isinstance(tree, _ALLOWED_ROOTS):
        return GuardResult(False, raw, f"Only SELECT queries are allowed (got {type(tree).__name__}).")

    # No forbidden node anywhere in the tree.
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN):
            return GuardResult(False, raw, f"Disallowed operation: {type(node).__name__}.")

    # Enforce a row limit if none present.
    limit_applied = False
    if tree.args.get("limit") is None:
        try:
            tree = tree.limit(config.DEFAULT_ROW_LIMIT)
            limit_applied = True
        except Exception:
            pass  # DB-level max_result_rows is the backstop

    cleaned = tree.sql(dialect=config.SQL_DIALECT)
    # Safety net: if sqlglot's .limit() call silently failed, add it via string
    if limit_applied and "LIMIT" not in cleaned.upper():
        cleaned = f"{cleaned} LIMIT {config.DEFAULT_ROW_LIMIT}"
    return GuardResult(True, cleaned, None, limit_applied)


def _regex_fallback(raw: str) -> GuardResult:
    """Used only when sqlglot cannot parse the SQL (e.g. an exotic ClickHouse
    function). Conservative: must start with SELECT/WITH and contain no
    forbidden keywords."""
    if not re.match(r"^\s*(with|select)\b", raw, re.IGNORECASE):
        return GuardResult(False, raw, "Only SELECT queries are allowed.")
    if _FORBIDDEN_WORDS.search(raw):
        return GuardResult(False, raw, "Query contains a disallowed keyword.")
    limit_applied = False
    cleaned = raw
    if not re.search(r"\blimit\b", raw, re.IGNORECASE):
        cleaned = f"{raw} LIMIT {config.DEFAULT_ROW_LIMIT}"
        limit_applied = True
    return GuardResult(True, cleaned, None, limit_applied)
