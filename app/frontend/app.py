"""Streamlit UI for the Turtlemint NL-SQL tool — full agentic pipeline.

Flow: ask -> (Prompt Enhancer, Intent, Table Agent) -> confirm tables ->
(Prune, SQL Generator, Guardrails) -> preview SQL -> run -> (Executor, Result
Formatter) -> summary + table + chart. Supports in-thread refinement.

Run with:  streamlit run app/frontend/app.py
"""
import base64
import os
import sys
from pathlib import Path

# Make `from app...` imports work no matter how Streamlit launches this file.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st

# Bridge Streamlit Cloud secrets into env vars BEFORE any backend import, so
# config picks up GEMINI_API_KEY / NLSQL_INPROCESS etc.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

import pandas as pd  # noqa: E402

from app.frontend.client import ensure_seeded, get_client  # noqa: E402

_client = get_client()
if _client.in_process:
    ensure_seeded()


@st.cache_data
def _logo_uri() -> str:
    p = Path(__file__).parent / "logo.png"
    if not p.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


LOGO = _logo_uri()

EXAMPLES = [
    "How many partners signed up last month?",
    "Total premium by product type",
    "Top 5 partners by number of policies sold",
    "Which state has the highest health premium?",
    "How many claims are still pending settlement?",
    "Average commission per partner tier",
]

st.set_page_config(page_title="Turtlemint NL-SQL", page_icon="🐢", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; }
      .tm-header {
        display:flex; align-items:center; gap:14px; flex-wrap:wrap;
        padding:18px 22px; border-radius:16px; margin-bottom:20px;
        background:linear-gradient(90deg,#00B386 0%,#1FC196 60%,#3DD9A6 100%);
        box-shadow:0 6px 18px rgba(0,179,134,0.25);
      }
      .tm-logo { font-size:28px; font-weight:800; color:#FFFFFF; letter-spacing:-0.5px; }
      .tm-logo sup { font-size:16px; }
      .tm-logo-img { height:46px; width:46px; object-fit:contain;
                     background:#FFFFFF; border-radius:11px; padding:6px;
                     box-shadow:0 2px 6px rgba(0,0,0,0.12); }
      .tm-sub { color:#EAFFF8; font-size:15px; font-weight:500; }
      .tm-side-wrap { display:flex; align-items:center; gap:9px; margin-bottom:2px; }
      .tm-side-img { height:30px; width:30px; object-fit:contain; }
      .tm-side { font-size:22px; font-weight:800; color:#00875a; letter-spacing:-0.3px; }
      .tm-step { color:#00875a; font-weight:700; font-size:13px; text-transform:uppercase;
                 letter-spacing:0.5px; margin:6px 0 2px; }
      .tm-pill { display:inline-block; background:#EAF8F2; color:#00875a; font-weight:700;
                 padding:3px 12px; border-radius:999px; font-size:13px; border:1px solid #BFEADD; }
      button[kind="secondary"] {
        background:#FFFFFF; color:#0E8C6B; border:1.5px solid #BFEADD;
        border-radius:10px; font-weight:600;
      }
      button[kind="secondary"]:hover { background:#EAF8F2; border-color:#00B386; color:#00875a; }
      button[kind="primary"] { background:#00B386; border:none; border-radius:10px; font-weight:700; }
      button[kind="primary"]:hover { background:#00996F; }
      [data-testid="stMetricValue"] { color:#00875a; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- backend helpers (HTTP or in-process, via the client) ------------------
def api_get(path, **params):
    return _client.get(path, **params)


def api_post(path, payload, timeout=120):
    return _client.post(path, payload, timeout=timeout)


def add_usage(resp):
    u = (resp or {}).get("usage") or {}
    st.session_state.usage["calls"] += u.get("calls", 0)
    st.session_state.usage["prompt_tokens"] += u.get("prompt_tokens", 0)
    st.session_state.usage["completion_tokens"] += u.get("completion_tokens", 0)


def do_plan(question, previous=None):
    st.session_state.gen = None
    st.session_state.run = None
    st.session_state.usage = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
    with st.spinner("Understanding your question (enhancer → intent → tables)..."):
        plan = api_post("/plan", {"question": question, "previous": previous,
                                  "user_id": st.session_state.user_id})
    add_usage(plan)
    st.session_state.plan = plan
    if plan.get("ok"):
        st.session_state.enhanced = plan.get("enhanced_question", question)
        st.session_state.tables_ms = plan.get("selected_tables", [])


# --- session defaults ---
for key, default in {
    "user_id": "demo", "plan": None, "gen": None, "run": None,
    "enhanced": "", "sql_editor": "", "refine": "",
    "usage": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
}.items():
    st.session_state.setdefault(key, default)

# --- sidebar ---
with st.sidebar:
    st.markdown(
        '<div class="tm-side-wrap">'
        + (f'<img class="tm-side-img" src="{LOGO}"/>' if LOGO else "")
        + '<span class="tm-side">turtlemint<sup>+</sup></span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Ask data questions in plain English. Agentic pipeline (dummy data).")
    st.session_state.user_id = st.text_input("Your user id", st.session_state.user_id)

    health = api_get("/health")
    if not health:
        st.error("Backend not reachable. Start it first (see README).")
    else:
        st.success("Backend connected")
        st.caption(f"DB: `{health['db_backend']}` · Model: `{health['model']}` · "
                   f"Limit: {health['max_queries_per_day']}/day")
        if not health["llm_configured"]:
            st.warning("No LLM key set. Add `GEMINI_API_KEY` to `.env`.")

    u = st.session_state.usage
    if u["calls"]:
        st.caption(f"This question: {u['calls']} LLM calls · "
                   f"{u['prompt_tokens'] + u['completion_tokens']} tokens")

    schema = api_get("/schema")
    if schema:
        with st.expander("Schema (dummy OpenMetadata)"):
            for t in schema["catalog"]["tables"]:
                st.markdown(f"**{t['name']}** — {t['description']}")
                st.caption(", ".join(c["name"] for c in t["columns"]))

    with st.expander("Recent activity (audit)"):
        aud = api_get("/audit", user_id=st.session_state.user_id, limit=10)
        rows = (aud or {}).get("rows", [])
        if rows:
            st.dataframe(pd.DataFrame(rows)[["question", "success", "row_count", "latency_ms"]],
                         use_container_width=True, height=220)
        else:
            st.caption("No queries yet.")

# --- header ---
st.markdown(
    '<div class="tm-header">'
    + (f'<img class="tm-logo-img" src="{LOGO}"/>' if LOGO else "")
    + '<span class="tm-logo">turtlemint<sup>+</sup></span>'
    '<span class="tm-sub">Ask your data a question — in plain English</span>'
    '</div>',
    unsafe_allow_html=True,
)

# --- step 1: ask ---
st.write("Try an example:")
cols = st.columns(3)
for i, ex in enumerate(EXAMPLES):
    if cols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
        do_plan(ex)

question = st.text_input("Your question",
                         placeholder="e.g. How many motor policies lapsed this year?")
if st.button("Ask", type="primary") and question.strip():
    do_plan(question.strip())

# --- step 2: confirm tables ---
plan = st.session_state.plan
if plan is not None:
    if not plan.get("ok"):
        st.error(plan.get("error", "Could not plan the question."))
    else:
        st.markdown('<div class="tm-step">Step 1 · Understood</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            if plan.get("enhanced_question") and plan["enhanced_question"] != question:
                st.caption(f"Interpreted as: *{plan['enhanced_question']}*")
        with c2:
            if plan.get("intent"):
                st.markdown(f'<span class="tm-pill">{plan["intent"]}</span>',
                            unsafe_allow_html=True)

        st.markdown('<div class="tm-step">Step 2 · Confirm the tables</div>',
                    unsafe_allow_html=True)
        if plan.get("reason"):
            st.caption(plan["reason"])
        st.multiselect("Tables to use", options=plan.get("all_tables", []),
                       key="tables_ms")

        if st.button("Generate SQL", type="primary"):
            st.session_state.run = None
            with st.spinner("Writing SQL (prune → generate → guardrails)..."):
                gen = api_post("/generate", {
                    "question": st.session_state.enhanced,
                    "tables": st.session_state.tables_ms,
                    "user_id": st.session_state.user_id})
            add_usage(gen)
            st.session_state.gen = gen
            if gen.get("ok") and gen.get("guardrail_ok"):
                st.session_state.sql_editor = gen.get("sql", "")

# --- step 3: preview SQL ---
gen = st.session_state.gen
if gen is not None:
    if not gen.get("ok"):
        st.error(gen.get("error", "SQL generation failed."))
    elif not gen.get("guardrail_ok"):
        st.error(f"The generated query was blocked by guardrails: {gen.get('guardrail_error')}")
        with st.expander("Show the blocked SQL"):
            st.code(gen.get("raw_sql", ""), language="sql")
    else:
        st.markdown('<div class="tm-step">Step 3 · Review the SQL</div>', unsafe_allow_html=True)
        # Show schema source badge
        src = gen.get("schema_source", "catalog")
        if src == "live_api":
            st.success("🌐 Schema fetched live from OpenMetadata API")
        elif src == "mixed":
            st.info("🌐 Schema: live API (real tables) + catalog (dummy tables)")
        if gen.get("explanation"):
            st.info(gen["explanation"])
        st.text_area("SQL (you can edit it)", key="sql_editor", height=130)
        if gen.get("limit_applied"):
            st.caption("A safety row LIMIT was added automatically.")
        if st.button("Run query", type="primary"):
            with st.spinner("Running query..."):
                st.session_state.run = api_post("/run", {
                    "sql": st.session_state.sql_editor,
                    "question": st.session_state.enhanced,
                    "intent": (plan or {}).get("intent", ""),
                    "tables": st.session_state.tables_ms,
                    "user_id": st.session_state.user_id})
            add_usage(st.session_state.run)

# --- step 4: results ---
run = st.session_state.run
if run is not None:
    if not run.get("ok"):
        st.error(run.get("error", "Query failed."))
    else:
        st.markdown('<div class="tm-step">Step 4 · Answer</div>', unsafe_allow_html=True)
        if run.get("summary"):
            st.success(run["summary"])

        # Warn when 0 rows returned in sample-data mode
        if run["row_count"] == 0:
            st.warning(
                "⚠️ **0 rows found** — but this may not mean the record doesn't exist.\n\n"
                "The current mode (**api_duckdb**) searches only the **25 sample rows** "
                "returned by the OpenMetadata API, not the full ClickHouse database. "
                "The person or record you're looking for may exist in the full dataset.\n\n"
                "👉 To search the full database, engineering needs to set "
                "`DB_BACKEND=clickhouse_http` with real ClickHouse credentials."
            )

        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", run["row_count"])
        m2.metric("Time", f"{run['latency_ms']} ms")
        tok = run.get("usage", {})
        m3.metric("Tokens (this step)", tok.get("prompt_tokens", 0) + tok.get("completion_tokens", 0))

        if run["columns"]:
            df = pd.DataFrame(run["rows"], columns=run["columns"])
            st.dataframe(df, use_container_width=True)
            st.download_button("Download CSV", df.to_csv(index=False), "result.csv", "text/csv")
            chart = run.get("chart")
            if chart and chart.get("x") in df.columns and chart.get("y") in df.columns:
                try:
                    cdf = df.set_index(chart["x"])[[chart["y"]]]
                    (st.line_chart if chart.get("type") == "line" else st.bar_chart)(cdf)
                except Exception:
                    pass
        with st.expander("SQL that ran"):
            st.code(run["executed_sql"], language="sql")

        # --- refinement ---
        st.markdown('<div class="tm-step">Refine</div>', unsafe_allow_html=True)
        refine = st.text_input("Adjust this question",
                               placeholder="e.g. only last month, or break down by state",
                               key="refine")
        if st.button("Refine") and refine.strip():
            do_plan(refine.strip(), previous=st.session_state.enhanced)
            st.rerun()
