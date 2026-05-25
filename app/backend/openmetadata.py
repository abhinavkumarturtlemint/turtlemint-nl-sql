"""OpenMetadata client — four live APIs, no local storage.

APIs used (all cached):
  /search/table/?table=NAME           → Auto-discover FQN for any table name (5 min)
  /get_columns/?fqn=FQN               → Full column schema + rich descriptions (5 min)
  /pii_latest_sample_data/?table_fnq=FQN → 25 sample rows for DuckDB executor (5 min)
  /search/glossary/                   → Business term definitions (see glossary.py)

Tables are auto-discovered at runtime — /search/table/ resolves any short name
to its full FQN, so TABLE_FQN_MAP is just a seed/cache, not a fixed list.
"""
from __future__ import annotations

import os
import re
import time
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Config — all URLs configurable via .env
# ---------------------------------------------------------------------------

_BASE = "https://ninja.turtlemintinsurance.com/api/crm/openmetadata"

SAMPLE_URL       = os.getenv("OPENMETADATA_SAMPLE_URL",
                              f"{_BASE}/pii_latest_sample_data/")
COLUMNS_URL      = os.getenv("OPENMETADATA_COLUMNS_URL",
                              f"{_BASE}/get_columns/")
TABLE_SEARCH_URL = os.getenv("OPENMETADATA_TABLE_SEARCH_URL",
                              f"{_BASE}/search/table/")

_HEADERS = {"Content-Type": "application/json"}
_TIMEOUT = 10
CACHE_TTL = 300  # 5 minutes

# Seed FQN map — auto-expanded at runtime by /search/table/ API.
# Add more tables here as starting hints; any table not listed will be
# discovered automatically via the search API.
TABLE_FQN_MAP: Dict[str, str] = {
    "policydetail": "ch-spectrum.spectrum.spectrum.policydetail",
}

# BSON tables live in local .bson/.bson.gz files — they must NEVER be looked up
# via the OpenMetadata API, even if OpenMetadata happens to know about them.
_BSON_TABLES: set = {"leadorderinfo", "loanoffers"}

# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------

_sample_cache:  Dict[str, Tuple[str, float]]        = {}  # table  → (ctx_str, ts)
_columns_cache: Dict[str, Tuple[List[Dict], float]] = {}  # fqn    → (cols, ts)
_fqn_cache:     Dict[str, str]                       = {}  # table  → fqn (discovered)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# API 1 — /search/table/ : FQN discovery
# ---------------------------------------------------------------------------

def _resolve_fqn(table_name: str) -> Optional[str]:
    """Return the full FQN for a short table name.

    Priority:
      1. Hardcoded TABLE_FQN_MAP  (instant)
      2. In-session discovered cache  (instant)
      3. Live /search/table/ API call  (one HTTP request, result cached)
    """
    name = table_name.lower()
    if name in TABLE_FQN_MAP:
        return TABLE_FQN_MAP[name]
    if name in _fqn_cache:
        return _fqn_cache[name]
    try:
        resp = requests.get(
            TABLE_SEARCH_URL,
            params={"table": name},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        tables = resp.json().get("tables", [])
        if tables:
            fqn = tables[0]["fqn"]
            _fqn_cache[name] = fqn
            TABLE_FQN_MAP[name] = fqn   # expand map so executor can find it too
            return fqn
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# API 2 — /get_columns/ : rich column schema
# ---------------------------------------------------------------------------

def _fetch_columns(fqn: str) -> List[Dict]:
    """Call /get_columns/?fqn=FQN and return the column list. Cached 5 min."""
    if fqn in _columns_cache:
        cols, ts = _columns_cache[fqn]
        if time.time() - ts < CACHE_TTL:
            return cols
    try:
        resp = requests.get(
            COLUMNS_URL,
            params={"fqn": fqn},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        cols = resp.json().get("columns", [])
        _columns_cache[fqn] = (cols, time.time())
        return cols
    except Exception:
        # Return stale or empty — never crash the pipeline
        return _columns_cache.get(fqn, ([], 0))[0]


def get_column_prompt(table_name: str) -> str:
    """Build a rich LLM-ready schema description for a table.

    Uses /search/table/ → /get_columns/ to get every column with its
    data type and business description. This is what the SQL generator
    uses to understand the table — the richer this is, the better the SQL.
    """
    fqn = _resolve_fqn(table_name)
    if not fqn:
        return ""

    cols = _fetch_columns(fqn)
    if not cols:
        return ""

    lines = [f"Table: {table_name}  (FQN: {fqn})"]
    lines.append("Columns:")
    for col in cols:
        col_name = col.get("name", "")
        dtype    = col.get("dataType", col.get("dataTypeDisplay", "STRING"))
        raw_desc = _strip_html(col.get("description", ""))

        if raw_desc:
            # Keep first sentence of Business Use Case (most informative, max 160 chars)
            first = re.split(r"[.!?]", raw_desc)[0].strip()[:160]
            lines.append(f"  {col_name} ({dtype}): {first}")
        else:
            lines.append(f"  {col_name} ({dtype})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# API 3 — /pii_latest_sample_data/ : sample rows (used by executor)
# ---------------------------------------------------------------------------

def get_schema_context(table_name: str, force_refresh: bool = False) -> str:
    """Fetch 25 sample rows as a pipe-delimited context string.

    Format (parsed by executor._fetch_api_data to load rows into DuckDB):
      Table: <name>
      col1 | col2 | col3
      val1 | val2 | val3
      ...

    Also used as fallback LLM context when /get_columns/ is unavailable.
    """
    name = table_name.lower()
    if not force_refresh and name in _sample_cache:
        ctx, ts = _sample_cache[name]
        if time.time() - ts < CACHE_TTL:
            return ctx

    fqn = _resolve_fqn(name)
    if not fqn:
        return ""

    try:
        resp = requests.get(
            SAMPLE_URL,
            params={"table_fnq": fqn},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        ctx = resp.json().get("context_string", "")
        if ctx:
            _sample_cache[name] = (ctx, time.time())
        return ctx
    except Exception:
        return _sample_cache.get(name, ("", 0))[0]


# ---------------------------------------------------------------------------
# Pipeline interface
# ---------------------------------------------------------------------------

def schema_prompt_for_real_tables(
    tables: List[str],
) -> Tuple[List[str], List[str]]:
    """Split tables into real (OpenMetadata) vs dummy (catalog fallback).

    For each real table:
      1. /search/table/ resolves the FQN (or uses hardcoded map)
      2. /get_columns/ returns rich column schema + descriptions
      → injected into the SQL generator prompt

    Tables not found in OpenMetadata fall back to the hardcoded schema_catalog.

    Returns:
      real_contexts  — LLM-ready schema strings (one per real table)
      dummy_tables   — table names not found in OpenMetadata
    """
    real_contexts: List[str] = []
    dummy_tables:  List[str] = []

    for table in tables:
        # BSON tables always use local files — never hit the OpenMetadata API
        if table.lower() in _BSON_TABLES:
            dummy_tables.append(table)
            continue

        fqn = _resolve_fqn(table.lower())
        if fqn:
            prompt = get_column_prompt(table.lower())
            if prompt:
                real_contexts.append(prompt)
            else:
                # FQN found but /get_columns/ failed — fall back to catalog
                dummy_tables.append(table)
        else:
            dummy_tables.append(table)

    return real_contexts, dummy_tables


def known_tables() -> List[str]:
    """Return all table names with a known FQN (hardcoded + auto-discovered)."""
    return list(TABLE_FQN_MAP.keys())


def cache_status() -> Dict:
    return {
        "sample_cached":   len(_sample_cache),
        "columns_cached":  len(_columns_cache),
        "fqns_discovered": len(_fqn_cache),
        "total_known":     len(TABLE_FQN_MAP),
    }


def get_db_prefix() -> str:
    return "spectrum"
