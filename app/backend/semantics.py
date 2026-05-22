"""Semantic layer — replaces the RAG vector index entirely.

Instead of embedding-based retrieval the semantic layer uses a YAML catalog
that defines:
  - metrics       Named business KPIs with source tables + trigger keywords
  - dimensions    Filterable attributes (product_type, tier, state, …)
  - business_terms  Plain-English → SQL filter mappings ('lapsed', 'last month')
  - example_questions  Q→SQL pairs for few-shot prompting

Matching is simple keyword scanning — fast, deterministic, zero LLM/embedding
calls. The full YAML is ~60 lines; for ≤ ~200 metrics it all fits in one prompt.

Drop-in replacement for knowledge.retrieve() + knowledge.examples_block():
  semantics.get_tables(question)        → List[str]   (replaces retr.tables)
  semantics.get_context_prompt(question) → str        (replaces examples_text)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

_YAML_PATH = Path(__file__).parent / "semantics.yaml"
_catalog: Optional[Dict] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> Dict:
    global _catalog
    if _catalog is None:
        with open(_YAML_PATH, encoding="utf-8") as fh:
            _catalog = yaml.safe_load(fh)
    return _catalog


def _reload() -> None:
    """Force-reload from disk (useful in tests or after edits)."""
    global _catalog
    _catalog = None
    _load()


def _score(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in *text* as whole words (case-insensitive).

    Uses word-boundary matching so 'age' does not fire on 'average', etc.
    Multi-word keywords (e.g. 'last month') are checked as substring phrases
    after lowercasing.
    """
    t = text.lower()
    count = 0
    for kw in (keywords or []):
        kw_lower = kw.lower()
        if " " in kw_lower:
            # multi-word phrase: substring match is fine
            if kw_lower in t:
                count += 1
        else:
            # single word: require word-boundary on both sides
            if re.search(r"\b" + re.escape(kw_lower) + r"\b", t):
                count += 1
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_tables(question: str) -> List[str]:
    """Return the tables most likely needed to answer *question*.

    Scores each metric and dimension by keyword overlap with the question,
    then returns the union of tables for the best-matching entries.
    Falls back to all known tables if nothing scores.
    """
    cat = _load()
    table_scores: Dict[str, int] = {}

    for metric in cat.get("metrics", []):
        s = _score(question, metric.get("keywords", []))
        if s > 0:
            for t in metric.get("tables", []):
                table_scores[t] = table_scores.get(t, 0) + s

    for dim in cat.get("dimensions", []):
        s = _score(question, dim.get("keywords", []))
        if s > 0:
            t = dim.get("table")
            if t:
                table_scores[t] = table_scores.get(t, 0) + s

    if not table_scores:
        # Nothing matched — return every table mentioned in any metric
        return get_all_tables()

    # Sort by score descending; return top-scoring tables (up to 5)
    ranked = sorted(table_scores.items(), key=lambda x: -x[1])
    return [t for t, _ in ranked[:5]]


def get_context_prompt(question: str) -> str:
    """Build a compact prompt block with semantic context for the SQL generator.

    Includes:
      • Relevant metric descriptions (what KPIs map to which tables)
      • Matched business-term definitions (exact SQL filter wording)
      • Up to 2 similar example Q→SQL pairs for few-shot guidance
    """
    cat = _load()
    lines: List[str] = []

    # --- Relevant metrics ---------------------------------------------------
    rel_metrics = [
        m for m in cat.get("metrics", [])
        if _score(question, m.get("keywords", [])) > 0
    ]
    if rel_metrics:
        lines.append("RELEVANT METRICS:")
        for m in rel_metrics:
            tables_str = ", ".join(m.get("tables", []))
            lines.append(f"  • {m['label']}: {m['description']}  [tables: {tables_str}]")

    # --- Matched business terms ---------------------------------------------
    rel_terms = [
        bt for bt in cat.get("business_terms", [])
        if _score(question, bt.get("keywords", [])) > 0
    ]
    if rel_terms:
        lines.append("\nBUSINESS TERM DEFINITIONS (use these exact SQL filters):")
        for bt in rel_terms:
            lines.append(f"  • \"{bt['term']}\": {bt['definition']}")
            sql_filter = bt.get("sql_filter", "")
            if sql_filter:
                lines.append(f"    SQL filter → {sql_filter}"
                             + (f"  (table: {bt.get('table', '')})" if bt.get("table") else ""))

    # --- Similar example questions ------------------------------------------
    # Score examples by word-overlap with the question
    q_words = set(re.sub(r"[^a-z0-9 ]", "", question.lower()).split())
    scored_examples = []
    for ex in cat.get("example_questions", []):
        ex_words = set(re.sub(r"[^a-z0-9 ]", "", ex["question"].lower()).split())
        overlap = len(q_words & ex_words)
        if overlap >= 2:
            scored_examples.append((overlap, ex))
    scored_examples.sort(key=lambda x: -x[0])

    if scored_examples:
        lines.append("\nSIMILAR EXAMPLE QUERIES:")
        for _, ex in scored_examples[:2]:
            lines.append(f"  Q: {ex['question']}")
            lines.append(f"  SQL: {ex['sql'].strip()}")

    return "\n".join(lines)


def get_all_tables() -> List[str]:
    """Return every table name that appears in any metric definition."""
    cat = _load()
    tables: List[str] = []
    seen = set()
    for m in cat.get("metrics", []):
        for t in m.get("tables", []):
            if t not in seen:
                tables.append(t)
                seen.add(t)
    return tables


def dimensions_for(tables: List[str]) -> List[Dict]:
    """Return dimensions that belong to the given tables (for schema context)."""
    cat = _load()
    return [
        d for d in cat.get("dimensions", [])
        if d.get("table") in tables
    ]
