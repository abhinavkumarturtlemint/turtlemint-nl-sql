"""Live glossary client — Turtlemint OpenMetadata Glossary API.

Fetches business term definitions with embedded SQL routing notes, then
injects them into the SQL generator prompt so the LLM uses the exact
column names Turtlemint has defined for each concept.

API:
  POST https://ninja.turtlemintinsurance.com/api/crm/openmetadata/search/glossary
  ?glossaryTerm=<search_term>

Each term's description contains routing notes like:
  "OD premium analysis → premiumdetails_netodpremium"
  "Rollover volume → policydetail WHERE businesstype = 'ROLLOVER'"

These notes are extracted and surfaced directly to the SQL generator.

Cache: responses cached for CACHE_TTL seconds per search word.
"""
from __future__ import annotations

import os
import re
import time
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GLOSSARY_URL = os.getenv(
    "OPENMETADATA_GLOSSARY_URL",
    "https://ninja.turtlemintinsurance.com/api/crm/openmetadata/search/glossary",
)
_HEADERS = {"Content-Type": "application/json"}
_TIMEOUT = 10
CACHE_TTL = 600   # 10 minutes

# ---------------------------------------------------------------------------
# Cache  {search_word: ([GlossaryItem], fetched_at)}
# ---------------------------------------------------------------------------

_cache: Dict[str, Tuple[List[Dict], float]] = {}

# ---------------------------------------------------------------------------
# HTML strip
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_ROUTING_RE = re.compile(r"Routing note[:\s]*(.*?)(?:\n|$)", re.IGNORECASE | re.DOTALL)


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


def _extract_routing(description: str) -> str:
    """Pull out the 'Routing note:' section if present."""
    m = _ROUTING_RE.search(description)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return ""


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def _fetch(word: str) -> List[Dict]:
    """Call the glossary API for *word* and return the parsed term list."""
    if word in _cache:
        items, fetched_at = _cache[word]
        if time.time() - fetched_at < CACHE_TTL:
            return items
    try:
        resp = requests.post(
            GLOSSARY_URL,
            params={"glossaryTerm": word},
            headers=_HEADERS,
            data="",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("glossary", [])
        _cache[word] = (items, time.time())
        return items
    except Exception:
        # Return stale cache or empty list — never crash the pipeline
        return _cache.get(word, ([], 0))[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_context(question: str) -> str:
    """Return a compact glossary context block for the SQL generator.

    Extracts key nouns/terms from *question*, fetches matching glossary
    entries, and formats them as a prompt snippet with routing notes.
    """
    # Extract candidate search words (nouns ≥ 4 chars, no stop words)
    _STOP = {
        "what", "which", "where", "when", "show", "give", "list", "find",
        "many", "much", "have", "been", "that", "this", "with", "from",
        "last", "this", "year", "month", "week", "into", "over", "more",
        "less", "than", "each", "all", "per", "total", "count", "number",
        "how", "are", "the", "for", "and", "not", "does", "did",
    }
    words = [
        w.lower()
        for w in re.findall(r"[a-zA-Z]{4,}", question)
        if w.lower() not in _STOP
    ]
    # Also search for exact domain keywords regardless of length
    for kw in ["OD", "TP", "NCB", "IDV", "TW", "FW", "CV", "DP", "KAM", "BQP", "RM"]:
        if re.search(r"\b" + kw + r"\b", question, re.IGNORECASE):
            words.append(kw.lower())

    if not words:
        return ""

    # Deduplicate and cap at 5 API calls per question
    seen_fqns: set = set()
    matched_terms: List[Dict] = []

    for word in list(dict.fromkeys(words))[:5]:
        for item in _fetch(word):
            fqn = item.get("fqn", "")
            if fqn and fqn not in seen_fqns:
                seen_fqns.add(fqn)
                matched_terms.append(item)

    if not matched_terms:
        return ""

    # Build prompt block
    lines = ["TURTLEMINT BUSINESS GLOSSARY (use these definitions when writing SQL):"]
    for item in matched_terms:
        name = item.get("name", "")
        glossary_field = item.get("glossary") or {}
        glossary_name = glossary_field.get("name", "") if isinstance(glossary_field, dict) else str(glossary_field)
        raw_desc = _strip_html(item.get("description", ""))
        routing = _extract_routing(raw_desc)

        # Main definition (first sentence, max 120 chars)
        main_def = raw_desc.split("Routing note")[0].strip()
        first_sentence = re.split(r"[.!?]", main_def)[0].strip()[:120]

        entry = f"  • [{glossary_name}] {name}: {first_sentence}"
        if routing:
            # Routing note tells the LLM exactly which column/filter to use
            entry += f"\n    SQL routing → {routing[:200]}"
        lines.append(entry)

    return "\n".join(lines)


def search(term: str) -> List[Dict]:
    """Public search — returns raw glossary items for a given term."""
    return _fetch(term)


def cache_size() -> int:
    return len(_cache)
