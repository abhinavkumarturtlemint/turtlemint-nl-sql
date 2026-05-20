# Turtlemint NL-SQL (dummy data)

Ask data questions in plain English; get ClickHouse SQL, a plain-English answer,
a table, and a chart. Implements the full **QueryGPT-style agentic pipeline**
from the SOW (Phases 1–4):

```
Question
  → Prompt Enhancer        (clean / clarify)
  → Vector index retrieve   (semantic table + example lookup)   ← RAG knowledge layer
  → Intent Agent            (classify business domain)
  → Table Agent             → USER CONFIRMS the tables
  → Column Prune Agent      (drop irrelevant columns)
  → live schema fetch       (catalog; stand-in for OpenMetadata)
  → SQL Generator           (ClickHouse SQL + explanation)
  → Guardrails              (SELECT-only, LIMIT, timeout)
  → Executor                (chdb now / ClickHouse HTTP later)
  → Result Formatter        (plain-English summary + chart)
```

Each agent is a focused **Gemini** call. Until real Turtlemint data is ready it
runs on **dummy insurance data** inside **chdb** (ClickHouse's engine embedded in
Python — same SQL dialect, no server, no Docker).

## What you need

- Python 3.9+ (already on your Mac)
- A Google Gemini API key — get one at https://aistudio.google.com/apikey

## Quickest start (one click)

Your key is already in `.env`. Just **double-click `start.command`** (macOS).
On first run it installs everything, seeds the dummy data, starts the backend,
and opens the app in your browser. (Windows: use `start.bat`.)

Prefer the manual route? Read on.

## Setup (one time)

```bash
cd "/Users/abhinav_kumar/Desktop/Natural Language SQL Query"

make install                 # creates .venv and installs everything
cp .env.example .env         # then open .env and paste your GEMINI_API_KEY
make seed                    # loads dummy insurance data
```

## Run it

Open two terminals (both in the project folder):

```bash
make backend     # terminal 1 — FastAPI on http://127.0.0.1:8000
make frontend    # terminal 2 — Streamlit UI on http://localhost:8501
```

Then open **http://localhost:8501**. The flow is: **ask → confirm tables →
review SQL → run → answer**, with a **Refine** box for follow-ups.

A 2-minute end-user walkthrough is in [USER_GUIDE.md](USER_GUIDE.md).

## Dummy data (insurance domain)

| Table | What it holds | Rows |
|---|---|---|
| `partner` | Advisors (POSP) who sign up and sell policies | 300 |
| `customer` | End customers | 2,000 |
| `policy` | Policies sold (motor/health/life/travel) | 5,000 |
| `claim` | Claims against policies | ~1,270 |
| `commission` | Commission earned per policy | 5,000 |

Dates are seeded relative to today, so "last month / this year" questions work.

## Try these questions

- How many partners signed up last month?
- What is the total premium by product type?
- Top 5 partners by number of policies sold
- How many claims are still pending settlement?
- Average premium for health policies by state

## Guardrails (safety)

- **SELECT-only** — `sqlglot` parses the SQL and blocks INSERT/UPDATE/DELETE/DROP/etc.
- **No stacked queries** — multi-statement input is rejected (injection defence).
- **Auto LIMIT** — a row limit (default 1000) is added if the query has none.
- **Timeout + row backstop** — enforced at the database via ClickHouse settings.
- **Mandatory preview** — `/run` re-validates and only executes SQL you've seen.
- **Per-user daily cap** — `MAX_QUERIES_PER_DAY` (default 200) limits cost/abuse.
- **Audit log** — every question, SQL, result, latency, and token usage is written
  to `app/data/store/audit.db` (viewable in the sidebar "Recent activity").

## Evaluation (golden set)

```bash
make seed && python -m app.eval.run            # full set (stop the backend first)
python -m app.eval.run --limit 3               # quick subset
```

Scores intent accuracy, table recall, execution success, and result similarity
against [app/eval/golden_set.py](app/eval/golden_set.py). Grow the golden set with
real pilot questions over time.

## Project structure

```
app/
  backend/
    config.py          env-driven config (the dummy↔real switch lives here)
    schema_catalog.py  dummy schema + business defs (stand-in for OpenMetadata)
    embeddings.py      Gemini embeddings client
    knowledge.py       RAG vector index: build + semantic retrieve
    llm.py             Gemini client (OpenAI-compatible) + retries/fallback/usage
    agents/
      prompt_enhancer.py  intent_agent.py  table_agent.py
      column_prune.py     result_formatter.py
    sql_generator.py   SQL + explanation from pruned schema + examples
    guardrails.py      sqlglot SELECT-only + auto-LIMIT
    executor.py        chdb (dummy) / ClickHouse HTTP (real) — same interface
    pipeline.py        orchestrator: plan() → build_sql() → format_result()
    audit.py           SQLite audit log + rate-limit/recent helpers
    main.py            FastAPI: /health /schema /plan /generate /run /audit
  frontend/app.py      Streamlit multi-step UI (confirm tables, preview, refine)
  data/seed.py         loads the dummy data
  eval/                golden set + scorer
tests/                 pytest: guardrails + pipeline endpoints
```

## When real data arrives

The architecture is built; switching to real Turtlemint data is mostly config:

1. Set `DB_BACKEND=clickhouse_http` and `CLICKHOUSE_URL` / read-only user in `.env`.
2. Replace `schema_catalog.py` with a live OpenMetadata fetch (the hybrid schema
   strategy in the SOW) — `knowledge.py` and the agents already read schema
   through it, so callers don't change.
3. Re-run `python -m app.eval.run` with real golden questions to re-baseline.

## Tests

```bash
make test     # or: .venv/bin/python -m pytest -q
```

## Notes

- Re-seeding: **stop the backend first** (it holds the chdb store open), then `make seed`.
- Change the Gemini model with `GEMINI_MODEL=...` in `.env` (default `gemini-2.5-flash`).
  If you hit a quota error, try `gemini-2.5-flash-lite` (higher free-tier limits).
