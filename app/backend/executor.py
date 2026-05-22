"""Query executor — two backends, zero local storage.

  api_duckdb      (default)
      1. Calls Turtlemint OpenMetadata API to fetch live schema + sample data
      2. Loads the rows into an in-memory DuckDB table (no files, no chdb)
      3. Adapts ClickHouse SQL → DuckDB SQL (strips db prefix, translates fns)
      4. Executes and returns results

  clickhouse_http (production)
      Sends SQL directly to a real ClickHouse HTTP endpoint.
      Set DB_BACKEND=clickhouse_http + CLICKHOUSE_URL in .env when you have
      the connection details from engineering. No code change needed.

chdb has been removed entirely. All data comes from the API.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List

from app.backend import config


class ExecutorError(RuntimeError):
    pass


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


# ---------------------------------------------------------------------------
# Backend 1 — API + DuckDB in-memory (default)
# ---------------------------------------------------------------------------

def _fetch_api_data(table_name: str) -> List[dict]:
    """Call the OpenMetadata API and parse the pipe-delimited response into rows."""
    from app.backend import openmetadata

    ctx = openmetadata.get_schema_context(table_name)
    if not ctx:
        raise ExecutorError(
            f"No OpenMetadata schema/data available for table '{table_name}'. "
            "Add it to openmetadata.TABLE_FQN_MAP."
        )

    lines = [l.strip() for l in ctx.strip().split("\n") if l.strip()]

    # Find the header line (first non-"Table:" line)
    header_line = None
    data_lines = []
    for line in lines:
        if line.startswith("Table:"):
            continue
        if header_line is None:
            header_line = line
        else:
            data_lines.append(line)

    if not header_line:
        raise ExecutorError(f"Could not parse schema from OpenMetadata for '{table_name}'")

    cols = [c.strip() for c in header_line.split("|")]

    # Keep only rows that have real data (not separator lines)
    rows = []
    for line in data_lines:
        vals = [v.strip() for v in line.split("|")]
        if sum(1 for v in vals if v not in ("---", "", "None")) > 5:
            rows.append(dict(zip(cols, vals)))

    return rows


def _extract_table_names(sql: str) -> List[str]:
    """Pull all table references from a SQL string (handles db.table format)."""
    # Match  FROM x.y, JOIN x.y, FROM y, JOIN y
    pattern = r"(?:FROM|JOIN)\s+([\w]+\.[\w]+|[\w]+)"
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = []
    for m in matches:
        # Strip database prefix: spectrum.policydetail → policydetail
        parts = m.split(".")
        tables.append(parts[-1].lower())
    return list(dict.fromkeys(tables))  # unique, preserve order


def _adapt_sql_for_duckdb(sql: str) -> str:
    """Translate ClickHouse-specific SQL to DuckDB-compatible SQL.

    Handles:
      - db.table references  →  table  (strip database prefix)
      - toStartOfMonth(x)    →  date_trunc('month', x)
      - toYear(x)            →  year(x)
      - toMonth(x)           →  month(x)
      - toDate(x)            →  CAST(x AS DATE)
      - now()                →  current_timestamp
      - count()              →  count(*)
      - addMonths(x, n)      →  x + INTERVAL n MONTH
    """
    adapted = sql

    # Strip database prefix from table references (turtlemint.X or spectrum.X → X)
    adapted = re.sub(
        r'\b(?:turtlemint|spectrum)\.([\w]+)\b',
        r'\1',
        adapted,
        flags=re.IGNORECASE,
    )

    # ClickHouse date functions → DuckDB equivalents
    adapted = re.sub(
        r'\btoStartOfMonth\s*\(([^)]+)\)',
        r"date_trunc('month', \1)",
        adapted, flags=re.IGNORECASE,
    )
    adapted = re.sub(
        r'\btoYear\s*\(([^)]+)\)',
        r'year(\1)',
        adapted, flags=re.IGNORECASE,
    )
    adapted = re.sub(
        r'\btoMonth\s*\(([^)]+)\)',
        r'month(\1)',
        adapted, flags=re.IGNORECASE,
    )
    adapted = re.sub(
        r'\btoDate\s*\(([^)]+)\)',
        r'CAST(\1 AS DATE)',
        adapted, flags=re.IGNORECASE,
    )
    adapted = re.sub(
        r'\baddMonths\s*\(([^,]+),\s*([^)]+)\)',
        r'\1 + INTERVAL \2 MONTH',
        adapted, flags=re.IGNORECASE,
    )
    adapted = re.sub(
        r'\bparseDateTimeBestEffortOrNull\s*\(([^)]+)\)',
        r'TRY_CAST(\1 AS TIMESTAMP)',
        adapted, flags=re.IGNORECASE,
    )

    # now() → current_timestamp
    adapted = re.sub(r'\bnow\s*\(\s*\)', 'current_timestamp', adapted, flags=re.IGNORECASE)

    # count() → count(*)
    adapted = re.sub(r'\bcount\s*\(\s*\)', 'count(*)', adapted, flags=re.IGNORECASE)

    return adapted


def _run_api_duckdb(sql: str) -> QueryResult:
    """Fetch data from OpenMetadata API, load into DuckDB in-memory, run SQL."""
    import duckdb
    import pandas as pd

    from app.backend import openmetadata

    # Find which real tables the SQL references
    raw_tables = _extract_table_names(sql)
    known = set(openmetadata.known_tables())

    # Build in-memory DuckDB from API data
    con = duckdb.connect(":memory:")

    tables_loaded = []
    for table in raw_tables:
        if table in known:
            rows = _fetch_api_data(table)
            if rows:
                df = pd.DataFrame(rows)
                # Replace sentinel strings with NaN so pandas infers types correctly
                df = df.replace({"None": None, "---": None, "": None})
                # Auto-cast each column: try numeric first, then datetime, else keep string
                for col in df.columns:
                    numeric = pd.to_numeric(df[col], errors="coerce")
                    if numeric.notna().sum() > 0:
                        df[col] = numeric
                        continue
                    # Try datetime for columns with date-like names
                    if any(kw in col.lower() for kw in ("date", "at", "time", "dt")):
                        try:
                            dt = pd.to_datetime(df[col], errors="coerce")
                            if dt.notna().sum() > 0:
                                df[col] = dt
                                continue
                        except Exception:
                            pass
                # Register as DuckDB table
                con.register(table, df)
                tables_loaded.append(table)

    if not tables_loaded:
        raise ExecutorError(
            f"None of the tables in the SQL ({raw_tables}) are available via "
            "the OpenMetadata API. Add them to openmetadata.TABLE_FQN_MAP or "
            "provide ClickHouse credentials (DB_BACKEND=clickhouse_http)."
        )

    # Adapt SQL: ClickHouse dialect → DuckDB dialect
    adapted_sql = _adapt_sql_for_duckdb(sql)

    # Strip SETTINGS clause if present (ClickHouse-only)
    adapted_sql = re.sub(r'\s*SETTINGS\s+.*$', '', adapted_sql, flags=re.IGNORECASE | re.DOTALL)

    # Apply row limit
    if not re.search(r'\bLIMIT\b', adapted_sql, re.IGNORECASE):
        adapted_sql += f" LIMIT {config.DEFAULT_ROW_LIMIT}"

    try:
        result = con.execute(adapted_sql).fetchdf()
    except Exception as e:
        raise ExecutorError(f"Query failed: {e}\n\nAdapted SQL:\n{adapted_sql}") from e

    columns = list(result.columns)
    rows = result.values.tolist()
    return QueryResult(columns=columns, rows=rows, row_count=len(rows))


# ---------------------------------------------------------------------------
# Backend 2 — Real ClickHouse over HTTP (production path)
# ---------------------------------------------------------------------------

_ch_client = None


def _get_ch_client():
    global _ch_client
    if _ch_client is None:
        import clickhouse_connect
        if not config.CLICKHOUSE_URL:
            raise ExecutorError(
                "CLICKHOUSE_URL is not set. "
                "Add it to .env to connect to real ClickHouse."
            )
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
        result = client.query(
            sql, settings={"max_execution_time": config.QUERY_TIMEOUT_S}
        )
    except Exception as e:
        raise ExecutorError(str(e)) from e
    columns = list(result.column_names)
    rows = [list(r) for r in result.result_rows]
    return QueryResult(columns=columns, rows=rows, row_count=len(rows))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(sql: str) -> QueryResult:
    """Execute *sql* using the configured backend.

    DB_BACKEND=api_duckdb     → OpenMetadata API + DuckDB in-memory (default)
    DB_BACKEND=clickhouse_http → real ClickHouse HTTP endpoint
    """
    if config.DB_BACKEND == "api_duckdb":
        return _run_api_duckdb(sql)
    if config.DB_BACKEND == "clickhouse_http":
        return _run_clickhouse_http(sql)
    # Legacy chdb path removed — if someone still has DB_BACKEND=chdb, redirect
    if config.DB_BACKEND == "chdb":
        raise ExecutorError(
            "chdb backend has been removed. "
            "Set DB_BACKEND=api_duckdb in your .env file."
        )
    raise ExecutorError(f"Unknown DB_BACKEND: {config.DB_BACKEND!r}")
