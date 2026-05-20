# NL-SQL Project — Conversation Summary

**Project:** Natural Language SQL Query Processor (for Turtlemint, internal tool)
**Period covered:** 18–20 May 2026
**Location:** `F:\Natural Language SQL Query\`

---

## 1. The starting point

You wanted to build a tool that lets non-technical business users at Turtlemint ask data questions in plain English and get correct SQL-backed answers — without learning SQL or waiting on analysts. You asked for feasibility, tech stacks, and questions to clarify the requirements.

**Initial answer:** highly feasible — this is a mature LLM use case ("Text-to-SQL"). The hard part isn't generating SQL; it's making it accurate, safe, and trustworthy for users who can't spot a wrong query.

**Three classic approaches discussed:**
- **Simple prompt-to-SQL** (MVP, ~1–2 weeks)
- **RAG + semantic layer** (production-grade)
- **Agentic with self-correction** (most accurate)

---

## 2. Concepts we covered along the way

### cURL
A command-line tool to send HTTP requests to APIs. **Not part of the final product** — it's a testing/debugging tool. Every "edge" in our architecture (backend → Claude, backend → OpenMetadata, backend → ClickHouse endpoint) is an HTTP call, and cURL is how you poke each of those edges by hand during build, debug, or incident triage.

### The `clickhouse_query_run` endpoint
You shared a Turtlemint internal URL. Decoded, it runs a ClickHouse query passed via URL. Key takeaways:
- Confirmed Turtlemint uses **ClickHouse** as the data warehouse
- Confirmed an existing **HTTP execution endpoint** that takes raw SQL
- Flagged: must confirm with engineering that the endpoint is **read-only and authenticated** before building on it

### Guardrails
The safety checks between AI output and the database. Concretely:
1. Read-only database user (physical limit)
2. SQL parser allows only `SELECT` (logical limit)
3. Auto-append `LIMIT 1000`
4. Query timeout (~30s)
5. Mandatory SQL preview before run
6. Plain-English explanation alongside the SQL
7. Audit log of every action
8. Per-user query cap

**Mental model:** the LLM is a smart-but-careless intern; guardrails are the senior reviewer.

### What "RAG" actually means
**Retrieval-Augmented Generation** — *first retrieve relevant notes, then have the AI answer using them.* RAG is how Claude learns about Turtlemint's specific data (because it doesn't know it cold). It's **one part** of the system, not the whole thing.

The full system = **RAG (knowledge) + Agent Pipeline (reasoning) + Guardrails (safety).**

---

## 3. Uber's QueryGPT (reference architecture)

We researched Uber's production system. Key facts:
- Handles ~1.2M queries/month
- Cut query time from ~10 min to ~3 min
- 78% of users report time savings

**Their v1 (failed at scale):** simple RAG → all-in-one LLM call. Hit three traps: bad retrieval, no intent step, schema too big for the model's memory.

**Their v2 (works in production):** a pipeline of specialised agents:
1. **Workspaces** — pre-grouped domains (Mobility, Ads, etc.)
2. **Intent Agent** — classifies which domain
3. **Table Agent** — picks tables, asks user to confirm
4. **Column Prune Agent** — strips irrelevant columns
5. **Generation** — writes the SQL

**The headline lesson:** *"One LLM doing everything fails. Multiple LLMs each doing one narrow thing succeeds."*

**Important nuance:** "agent" doesn't mean a separately-trained AI. It means **the same LLM (GPT-4 Turbo in Uber's case, Claude in ours) called with a different focused instruction each time.** One brain, many sticky notes.

**Why GPT-4 Turbo for Uber:**
1. 128K context window — needed to fit huge table definitions
2. Strongest reasoning available when they built it (2023–24)
3. Existing OpenAI enterprise contract

We're using **Claude** instead — equally strong choice today, and the architecture is model-agnostic.

---

## 4. The big architecture decision — where do schemas live?

We went through this carefully because your instinct ("don't store schemas in the knowledge base") pointed at a real risk: **stored schemas go stale.**

We ruled out two extremes:
- ❌ **Store everything in our KB** — duplicates source of truth, drifts out of date
- ❌ **Call OpenMetadata API for everything** — APIs can't search by meaning, so finding the right table is impossible

We landed on the **hybrid**:

| What | Stored where | Why |
|---|---|---|
| **Lightweight index** (table names + 1-line summaries) | Our vector DB | Needed for semantic search ("find tables about partner signups") |
| **Full schema** (columns, types, descriptions) | OpenMetadata only — fetched **live** each time | Always current; never stale |
| **Example Q→SQL pairs** | Our knowledge file | OpenMetadata doesn't hold these — only humans can author them |
| **Business definitions** | Our knowledge file | Same reason |

**The key insight:** the (possibly stale) index is only used to **find candidate tables**. The actual schema used to **write the SQL** is always fetched live. A stale index can occasionally misroute a question (caught by the user-confirm step) — but it can **never produce wrong SQL**.

### The "separate schema DB" option (and why we rejected it)
Late in the conversation you asked about a fully independent schema DB. Honest verdict: it doesn't work, because the schema data still has to come from somewhere — and that somewhere is OpenMetadata or ClickHouse. You'd either duplicate effort or add a useless middleman.

**The future upgrade path:** post-MVP, consider building a thin "Schema Service" that wraps OpenMetadata *and* holds your business definitions and example queries — a clean single API for the backend.

---

## 5. The final architecture (as it stands)

### The 9-stage pipeline
A question flows through:

1. **Prompt Enhancer** — cleans messy input *(Claude call)*
2. **Intent Agent** — picks the business domain *(Claude call + vector index lookup)*
3. **Table Agent** — selects tables → **shows user to confirm** *(Claude call)*
4. **Live Schema Fetch** — `GET /tables/x` from OpenMetadata *(HTTP call, no AI)*
5. **Column Prune Agent** — drops irrelevant columns *(Claude call)*
6. **SQL Generator** — writes ClickHouse SQL + plain-English explanation *(Claude call + knowledge file lookup)*
7. **Guardrails** — `SELECT`-only, `LIMIT`, timeout *(deterministic code, no AI)*
8. **Executor** — calls `clickhouse_query_run` *(HTTP call, no AI)*
9. **Result Formatter** — table/chart + summary *(Claude call)*

Six stages call Claude (same model, different prompt each time). Two stages are pure code. One stage involves the human user.

### Supporting components
- **Nightly Sync Job** — refreshes the vector index from OpenMetadata
- **Audit Log** — every question, generated SQL, result, latency, user

### Tech stack
| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| Backend | Python + FastAPI |
| LLM | Claude (Anthropic API) |
| RAG framework | Vanna.ai |
| Vector DB | Chroma |
| SQL safety parser | sqlglot |
| Source of truth | OpenMetadata (existing at Turtlemint) |
| Database | ClickHouse (existing at Turtlemint) |
| Execution | `clickhouse_query_run` endpoint (existing) |

---

## 6. The build plan (5 weeks, 4 phases)

| Phase | Weeks | Goal |
|---|---|---|
| **Phase 0** | Days 1–3 | Confirm access (`clickhouse_query_run`, OpenMetadata API, Anthropic), identify pilot team, collect 20–30 example Q→SQL pairs, lock business definitions |
| **Phase 1 — Spine** | Week 1 | Single Claude call → guardrails → execute → show. 5 hand-picked questions answered correctly |
| **Phase 2 — Knowledge base** | Week 2 | Add Vanna + vector index + live OpenMetadata fetch. ≥70% golden-set accuracy |
| **Phase 3 — Agent pipeline** | Weeks 3–4 | Add Prompt Enhancer, Intent, Table-with-confirm, Prune. ≥85% accuracy |
| **Phase 4 — Harden & pilot** | Week 5 | Audit log, rate limits, onboarding doc, pilot with 5 Operations users |

---

## 7. Key product/PM decisions to drive

These are *your* job, not engineering's:

1. Identify the pilot business team (recommend Operations)
2. Collect 20–30 real questions + the SQL an analyst would write for each — *the most valuable artefact in the project*
3. Lock business definitions across teams ("active partner", "lapsed policy", "settled claim", etc.)
4. Define 4–6 domains for the Intent Agent
5. Set the trust bar — when does the tool auto-run vs. require confirm?
6. Recruit pilot users; run weekly office hours

---

## 8. Open questions to take to Turtlemint engineering / data team

1. Is `clickhouse_query_run` read-only and authenticated? If not, can a read-only equivalent be provisioned?
2. Does OpenMetadata expose tables and full schema via REST API? What are the endpoints and auth?
3. Does OpenMetadata emit change webhooks, or do we sync via polling?
4. Is Anthropic API approved for internal use?
5. Is a lightweight schema index on our side acceptable under governance, or must we use OpenMetadata's own search?
6. What is the deployment target (Kubernetes, VM, internal PaaS)?
7. What's the monthly LLM budget ceiling?

---

## 9. Deliverables produced during the conversation

| File | Purpose |
|---|---|
| `NL-SQL-Explained.docx` | Plain-language explainer of the whole concept (Word doc, ~8 sections + glossary) |
| `NL-SQL-SOW.docx` | Detailed Statement of Work (18 sections — scope, phases, risks, deps, governance) |
| `NL-SQL-Architecture.md` | Mermaid architecture diagram in markdown |
| `NL-SQL-Architecture.png` | Rendered PNG of the diagram |
| `NL-SQL-Architecture.svg` | Vector version of the diagram |
| `generate_doc.js` | Generator script for the explainer Word doc |
| `generate_sow.js` | Generator script for the SOW Word doc |
| `Conversation-Summary.md` | This document |

---

## 10. The whole project in one paragraph

> Business users at Turtlemint cannot write SQL but need data answers. The project builds an internal tool that translates plain-English questions into ClickHouse SQL using Claude. The architecture follows Uber's QueryGPT pattern — a pipeline of small specialised AI "agents" (each a focused Claude call) wrapped around a hybrid schema strategy: a lightweight vector index for fast semantic discovery of relevant tables, plus a live API fetch from OpenMetadata at SQL-generation time so the SQL is always written against the current schema. Safety is enforced by a deterministic guardrails layer (read-only DB user, SQL-parse, row limits) and human-in-the-loop confirmation at the table-selection step. The MVP runs in 5 weeks for one pilot team, with a golden Q→SQL evaluation set as the accuracy benchmark.

---

## 11. Quick glossary

| Term | Meaning |
|---|---|
| **SQL** | The technical language used to query databases — the thing we hide from users |
| **ClickHouse** | Turtlemint's data warehouse |
| **OpenMetadata** | Turtlemint's data catalog — the source of truth for schemas |
| **LLM** | Large Language Model (Claude in our case) |
| **Agent** | One LLM call given one narrow task. Same model, different instruction = different "agent" |
| **RAG** | Retrieval-Augmented Generation — fetch relevant context, then ask the AI |
| **Vector DB** | A database that searches by meaning (semantic), not exact match |
| **Guardrails** | Code-based safety checks between AI output and the database |
| **Golden set** | A maintained list of question→correct-SQL pairs used to score every change |
| **Vanna.ai** | Library that handles the RAG plumbing for text-to-SQL |
| **sqlglot** | Python library that parses SQL — used to enforce SELECT-only |
| **Streamlit** | Python framework for fast internal-tool UIs |
| **FastAPI** | Python web framework — hosts the backend pipeline |
| **cURL** | Command-line tool to make HTTP requests by hand — for testing, not in production |
