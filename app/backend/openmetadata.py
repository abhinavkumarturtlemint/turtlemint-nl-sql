"""Live schema fetcher from Turtlemint's OpenMetadata API.

Replaces the hardcoded schema_catalog for real tables.

API endpoint:
  GET https://ninja.turtlemintinsurance.com/api/crm/openmetadata/pii_latest_sample_data
  ?table_fnq=ch-spectrum.spectrum.spectrum.policydetail

The API returns a `context_string` that is already formatted for LLM injection
— it contains column names, types, sample rows, all pipe-delimited.
We pass this directly to the SQL generator instead of our hardcoded catalog.

Cache: responses are cached for CACHE_TTL seconds to avoid calling the API
on every query.

To add a new real table: add one line to TABLE_FQN_MAP below.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_BASE_URL = "https://ninja.turtlemintinsurance.com/api/crm/openmetadata/pii_latest_sample_data"
_HEADERS = {"Content-Type": "application/json"}
_TIMEOUT = 15          # seconds per API call
CACHE_TTL = 300        # 5 minutes — refresh schema every 5 min

# ---------------------------------------------------------------------------
# Table registry
# Map our short table names → full OpenMetadata FQN (table_fnq parameter)
# Add a new line here whenever you want to onboard a new real table.
# ---------------------------------------------------------------------------

TABLE_FQN_MAP: Dict[str, str] = {
    "policydetail": "ch-spectrum.spectrum.spectrum.policydetail",
    # "leaddetail":   "ch-spectrum.spectrum.spectrum.leaddetail",
    # "partnerdetail":"ch-spectrum.spectrum.spectrum.partnerdetail",
    # Add more tables here as you discover their FQNs
}

# DB prefix to use in generated SQL for each FQN source
# FQN "ch-spectrum.spectrum.spectrum.X" → SQL prefix "spectrum"
_FQN_TO_DB_PREFIX: Dict[str, str] = {
    "ch-spectrum": "spectrum",
}


# ---------------------------------------------------------------------------
# In-memory cache  {table_name: (context_string, fetched_at)}
# ---------------------------------------------------------------------------

_cache: Dict[str, Tuple[str, float]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def known_tables() -> List[str]:
    """Return the list of real tables this module can fetch schemas for."""
    return list(TABLE_FQN_MAP.keys())


def get_schema_context(table_name: str, force_refresh: bool = False) -> Optional[str]:
    """Fetch live schema + sample data for *table_name* from OpenMetadata.

    Returns the `context_string` (ready for LLM injection) or None if
    the table is not in TABLE_FQN_MAP or the API call fails.

    The result is cached for CACHE_TTL seconds.
    """
    if table_name not in TABLE_FQN_MAP:
        return None

    # Check cache
    if not force_refresh and table_name in _cache:
        ctx, fetched_at = _cache[table_name]
        if time.time() - fetched_at < CACHE_TTL:
            return ctx

    fqn = TABLE_FQN_MAP[table_name]
    try:
        resp = requests.get(
            _BASE_URL,
            params={"table_fnq": fqn},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        ctx = data.get("context_string", "")
        if ctx:
            _cache[table_name] = (ctx, time.time())
            return ctx
    except Exception as e:
        # Log but don't crash — caller falls back to hardcoded catalog
        import sys
        print(f"[openmetadata] WARNING: could not fetch schema for {table_name}: {e}",
              file=sys.stderr)

    # Return stale cache if we have one (better than nothing)
    if table_name in _cache:
        return _cache[table_name][0]
    return None


def get_db_prefix(table_name: str) -> str:
    """Return the SQL database prefix for a table, e.g. 'spectrum'."""
    fqn = TABLE_FQN_MAP.get(table_name, "")
    source = fqn.split(".")[0] if fqn else ""
    return _FQN_TO_DB_PREFIX.get(source, "turtlemint")


def schema_prompt_for_real_tables(tables: List[str]) -> Tuple[List[str], List[str]]:
    """Split *tables* into (real_tables, dummy_tables).

    For real tables, fetch context_string from OpenMetadata.
    Returns (real_context_strings, dummy_table_names).
    """
    real_contexts: List[str] = []
    dummy_tables: List[str] = []

    for t in tables:
        ctx = get_schema_context(t)
        if ctx:
            real_contexts.append(ctx)
        else:
            dummy_tables.append(t)

    return real_contexts, dummy_tables


def cache_status() -> Dict[str, str]:
    """Return cache status for each known table (for /health endpoint)."""
    now = time.time()
    out = {}
    for t in TABLE_FQN_MAP:
        if t in _cache:
            age = int(now - _cache[t][1])
            out[t] = f"cached ({age}s ago)"
        else:
            out[t] = "not fetched"
    return out
