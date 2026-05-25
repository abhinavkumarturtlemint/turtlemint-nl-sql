"""Query executor — three backends, zero local storage.

  api_duckdb      (default)
      1a. For OpenMetadata tables: calls Turtlemint API → pipe-delimited rows
      1b. For BSON tables: loads .bson.gz file → flattens nested fields
      2.  Loads all rows into an in-memory DuckDB table
      3.  Adapts ClickHouse SQL → DuckDB SQL (strips db prefix, translates fns)
      4.  Executes and returns results

  clickhouse_http (production)
      Sends SQL directly to a real ClickHouse HTTP endpoint.
      Set DB_BACKEND=clickhouse_http + CLICKHOUSE_URL in .env when you have
      the connection details from engineering. No code change needed.

chdb has been removed entirely. All data comes from the API or local BSON files.
"""
from __future__ import annotations

import gzip
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from app.backend import config

# ---------------------------------------------------------------------------
# BSON table registry — maps short table name → path relative to project root
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BSON_TABLE_MAP: Dict[str, str] = {
    "leadorderinfo": os.path.join(
        _PROJECT_ROOT, "Sachet-DB-Stage", "turtlefin", "LeadOrderInfo.bson.gz"
    ),
    "loanoffers": os.path.join(
        _PROJECT_ROOT, "Sachet-DB-Stage-Loanoffers", "turtlefin", "LoanOffers.bson.gz"
    ),
}


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


# ---------------------------------------------------------------------------
# Backend 1b — Local BSON file loader
# ---------------------------------------------------------------------------

# Top-level keys that are deeply nested internal request/response mirrors —
# skipping them halves column count and removes duplicate data.
_BSON_SKIP = {
    "leadservicedata", "externalleaddata", "leadstageinfo",
    "analyticsdata", "initialleadentry", "consentmap",
    "dashboardsummarycount", "mis", "otherdetails",
    "currentleadactor", "rejecttracking",
}


def _flatten_doc(doc: dict, prefix: str = "", sep: str = "_") -> dict:
    """Recursively flatten a nested dict, lowercasing all keys."""
    out: dict = {}
    for k, v in doc.items():
        key = (prefix + sep + k if prefix else k).lower().replace("-", "_")
        base = key.split(sep)[0]
        if base in _BSON_SKIP:
            continue
        if isinstance(v, dict):
            out.update(_flatten_doc(v, key, sep))
        elif isinstance(v, list):
            # Don't recurse into lists here — handled separately for offers[]
            pass
        else:
            out[key] = None if v is None else str(v)
    return out


def _load_bson_table(table_name: str) -> "pd.DataFrame":
    """Load a .bson.gz file into a pandas DataFrame.

    Flattens nested fields with _ separator (lowercase).
    For loanoffers: explodes the offers[] array so each offer = one row.
    """
    import pandas as pd

    path = BSON_TABLE_MAP.get(table_name.lower())
    if not path or not os.path.exists(path):
        raise ExecutorError(
            f"BSON file not found for table '{table_name}': {path}"
        )

    try:
        import bson as _bson
    except ImportError:
        raise ExecutorError(
            "pymongo is required to read BSON files. "
            "Run: .venv/bin/pip install pymongo"
        )

    with gzip.open(path, "rb") as fh:
        raw = fh.read()

    records = []
    offset = 0
    while offset < len(raw):
        size = int.from_bytes(raw[offset: offset + 4], "little")
        if size <= 0 or offset + size > len(raw):
            break
        doc = _bson.decode(raw[offset: offset + size])

        if table_name.lower() == "loanoffers":
            # Explode offers[] — one row per offer, parent fields repeated
            parent = _flatten_doc(doc)
            offers = doc.get("offers", [])
            if offers:
                for offer in offers:
                    row = dict(parent)
                    for ok, ov in offer.items():
                        if not isinstance(ov, (dict, list)):
                            row["offer_" + ok.lower()] = None if ov is None else str(ov)
                    records.append(row)
            else:
                records.append(parent)
        else:
            records.append(_flatten_doc(doc))

        offset += size

    if not records:
        raise ExecutorError(f"No records found in BSON file for '{table_name}'")

    df = pd.DataFrame(records)
    df = df.replace({"None": None, "nan": None, "": None})

    # Auto-cast numeric and datetime columns.
    # Use a low threshold (5%) because MongoDB documents are sparse —
    # many fields are absent/null for docs where they don't apply, but
    # the column is still genuinely numeric when present.
    for col in df.columns:
        num = pd.to_numeric(df[col], errors="coerce")
        if num.notna().sum() > max(1, len(df) * 0.05):  # >5% numeric → cast
            df[col] = num
            continue
        if any(kw in col for kw in ("date", "at", "time")):
            try:
                dt = pd.to_datetime(df[col], errors="coerce", format="mixed", utc=True)
                if dt.notna().sum() > 0:
                    df[col] = dt
            except Exception:
                pass

    return df


def _extract_table_names(sql: str) -> List[str]:
    """Pull all table references from a SQL string (handles multi-level FQNs with hyphens).

    Examples handled:
      FROM policydetail
      FROM spectrum.policydetail
      FROM ch-spectrum.spectrum.spectrum.policydetail
    Always returns just the final table name (last dot-separated segment).
    """
    # Allow hyphens in each segment (ch-spectrum is a valid ClickHouse db name)
    pattern = r"(?:FROM|JOIN)\s+((?:[\w\-]+\.)*[\w]+)"
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = []
    for m in matches:
        # Take only the last segment: ch-spectrum.spectrum.spectrum.policydetail → policydetail
        parts = m.split(".")
        tables.append(parts[-1].lower())
    return list(dict.fromkeys(tables))  # unique, preserve order


def _adapt_sql_for_duckdb(sql: str) -> str:
    """Translate ClickHouse-specific SQL to DuckDB-compatible SQL.

    Handles:
      - db.table references       →  table  (strip database prefix)
      - toStartOfMonth(x)         →  date_trunc('month', x)
      - toYear(x)                 →  year(x)
      - toMonth(x)                →  month(x)
      - toDate(x)                 →  CAST(x AS DATE)
      - now()                     →  current_timestamp
      - count()                   →  count(*)
      - addMonths(x, n)           →  x + INTERVAL n MONTH
      - countIf(cond)             →  count(*) FILTER (WHERE cond)
      - toFloat64OrNull(x)        →  TRY_CAST(x AS DOUBLE)
      - toInt64OrNull(x)          →  TRY_CAST(x AS BIGINT)
    """
    adapted = sql

    # Strip any multi-level FQN prefix in FROM/JOIN clauses.
    # Handles: ch-spectrum.spectrum.spectrum.policydetail → policydetail
    #          spectrum.policydetail → policydetail
    #          turtlemint.policy → policy
    adapted = re.sub(
        r'\b(FROM|JOIN)\s+((?:[\w\-]+\.)+)([\w]+)',
        lambda m: f"{m.group(1)} {m.group(3)}",
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

    # countIf(cond) → count(*) FILTER (WHERE cond)
    adapted = re.sub(
        r'\bcountIf\s*\(([^)]+)\)',
        r'count(*) FILTER (WHERE \1)',
        adapted, flags=re.IGNORECASE,
    )

    # toFloat64OrNull(x) → TRY_CAST(x AS DOUBLE)
    adapted = re.sub(
        r'\btoFloat64OrNull\s*\(([^)]+)\)',
        r'TRY_CAST(\1 AS DOUBLE)',
        adapted, flags=re.IGNORECASE,
    )

    # toInt64OrNull(x) → TRY_CAST(x AS BIGINT)
    adapted = re.sub(
        r'\btoInt64OrNull\s*\(([^)]+)\)',
        r'TRY_CAST(\1 AS BIGINT)',
        adapted, flags=re.IGNORECASE,
    )

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
            # --- OpenMetadata API table ---
            rows = _fetch_api_data(table)
            if rows:
                df = pd.DataFrame(rows)
                df = df.replace({"None": None, "---": None, "": None})
                for col in df.columns:
                    numeric = pd.to_numeric(df[col], errors="coerce")
                    if numeric.notna().sum() > 0:
                        df[col] = numeric
                        continue
                    if any(kw in col.lower() for kw in ("date", "at", "time", "dt")):
                        try:
                            dt = pd.to_datetime(df[col], errors="coerce", format="mixed", utc=True)
                            if dt.notna().sum() > 0:
                                df[col] = dt
                                continue
                        except Exception:
                            pass
                con.register(table, df)
                tables_loaded.append(table)

        elif table in BSON_TABLE_MAP:
            # --- Local BSON file table ---
            df = _load_bson_table(table)
            con.register(table, df)
            tables_loaded.append(table)

    if not tables_loaded:
        bson_names = list(BSON_TABLE_MAP.keys())
        raise ExecutorError(
            f"None of the tables in the SQL ({raw_tables}) are available. "
            f"OpenMetadata tables: {list(known)}. "
            f"Local BSON tables: {bson_names}. "
            "Add the table to openmetadata.TABLE_FQN_MAP, BSON_TABLE_MAP, "
            "or set DB_BACKEND=clickhouse_http for real ClickHouse."
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
