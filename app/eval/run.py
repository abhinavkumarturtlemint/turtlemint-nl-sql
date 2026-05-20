"""Run the golden-set evaluation and print a scorecard.

Scores per the SOW: intent accuracy, table recall, execution success, and
result similarity (generated SQL result vs golden SQL result).

Usage:
    python -m app.eval.run            # full set
    python -m app.eval.run --limit 3  # quick subset

Note: needs database access. Stop the backend first (it holds the chdb store),
or point NLSQL_DATA_DIR at a separate seeded store.
"""
from __future__ import annotations

import argparse
from typing import Any, List

from app.backend import executor, pipeline
from app.eval.golden_set import GOLDEN


def _row_key(row: List[Any]):
    # Order-insensitive within a row so column ordering doesn't break matching.
    return tuple(sorted(str(round(v, 2) if isinstance(v, float) else v) for v in row))


def _result_set(rows: List[List[Any]]):
    return {_row_key(r) for r in rows}


def similarity(a_rows, b_rows) -> float:
    a, b = _result_set(a_rows), _result_set(b_rows)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def evaluate(item) -> dict:
    out = {"question": item["question"], "intent_match": 0, "table_recall": 0.0,
           "exec_ok": 0, "similarity": 0.0, "note": ""}
    try:
        plan = pipeline.plan(item["question"])
    except Exception as e:
        out["note"] = f"plan failed: {e}"
        return out

    out["intent_match"] = int(plan.intent == item["intent"])
    golden_tables = set(item["tables"])
    selected = set(plan.selected_tables)
    out["table_recall"] = len(golden_tables & selected) / len(golden_tables)

    try:
        sp = pipeline.build_sql(plan.enhanced_question, plan.selected_tables)
    except Exception as e:
        out["note"] = f"generation failed: {e}"
        return out
    if not sp.guardrail_ok:
        out["note"] = f"blocked: {sp.guardrail_error}"
        return out

    try:
        gen_rows = executor.run(sp.sql).rows
        out["exec_ok"] = 1
    except Exception as e:
        out["note"] = f"exec failed: {e}"
        return out

    try:
        gold_rows = executor.run(item["sql"]).rows
        out["similarity"] = round(similarity(gen_rows, gold_rows), 2)
    except Exception as e:
        out["note"] = f"golden exec failed: {e}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=len(GOLDEN))
    args = ap.parse_args()
    items = GOLDEN[: args.limit]

    print(f"Running golden-set eval on {len(items)} questions...\n")
    results = []
    for item in items:
        r = evaluate(item)
        results.append(r)
        print(f"  {'OK ' if r['exec_ok'] else 'ERR'} "
              f"intent={'Y' if r['intent_match'] else 'n'} "
              f"tables={r['table_recall']:.2f} sim={r['similarity']:.2f}  "
              f"{r['question']}" + (f"  [{r['note']}]" if r["note"] else ""))

    n = len(results)
    print("\n=== Scorecard ===")
    print(f"  Intent accuracy:   {sum(r['intent_match'] for r in results)/n:.0%}")
    print(f"  Table recall:      {sum(r['table_recall'] for r in results)/n:.0%}")
    print(f"  Execution success: {sum(r['exec_ok'] for r in results)/n:.0%}")
    print(f"  Result similarity: {sum(r['similarity'] for r in results)/n:.0%}")


if __name__ == "__main__":
    main()
