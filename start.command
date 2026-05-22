#!/bin/bash
# =============================================================================
#  Turtlemint NL-SQL — Mac double-click launcher
#  Double-click this file in Finder to start the full application.
#  Closes both backend + frontend when you close the terminal window.
# =============================================================================

cd "$(dirname "$0")" || exit 1

echo ""
echo "  ████████╗██╗   ██╗██████╗ ████████╗██╗     ███████╗"
echo "     ██╔══╝██║   ██║██╔══██╗╚══██╔══╝██║     ██╔════╝"
echo "     ██║   ██║   ██║██████╔╝   ██║   ██║     █████╗  "
echo "     ██║   ██║   ██║██╔══██╗   ██║   ██║     ██╔══╝  "
echo "     ██║   ╚██████╔╝██║  ██║   ██║   ███████╗███████╗"
echo "     ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝"
echo "     Turtlemint NL-SQL  |  Plain English → ClickHouse"
echo ""

# ── Step 1: Create virtual environment on first run ──────────────────────────
if [ ! -d ".venv" ]; then
  echo "[ SETUP ] First run detected — creating virtual environment..."
  python3 -m venv .venv
  echo "[ SETUP ] Installing dependencies (this takes ~1 min)..."
  .venv/bin/python -m pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
  echo "[ SETUP ] Done."
  echo ""
fi

# ── Step 2: Verify .env exists ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "[ WARNING ] .env file not found!"
  echo "  Copy the example below into a file named .env:"
  echo ""
  echo "  GEMINI_API_KEY=your_key_here"
  echo "  GEMINI_MODEL=gemini-2.5-flash"
  echo "  DB_BACKEND=api_duckdb"
  echo "  OPENMETADATA_GLOSSARY_URL=https://ninja.turtlemintinsurance.com/api/crm/openmetadata/search/glossary"
  echo "  OPENMETADATA_SAMPLE_URL=https://ninja.turtlemintinsurance.com/api/crm/openmetadata/pii_latest_sample_data"
  echo ""
  read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# ── Step 3: Start the FastAPI backend ─────────────────────────────────────────
echo "[ BACKEND ] Starting on http://127.0.0.1:8000 ..."
.venv/bin/uvicorn app.backend.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level warning &
BACKEND_PID=$!

# Kill backend automatically when this script exits
trap 'echo ""; echo "[ STOP ] Shutting down..."; kill $BACKEND_PID 2>/dev/null; exit 0' EXIT INT TERM

# ── Step 4: Wait for backend to be ready ─────────────────────────────────────
echo "[ BACKEND ] Waiting for health check..."
READY=0
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.5
done

if [ "$READY" -eq 0 ]; then
  echo "[ ERROR ] Backend did not start in time. Check for errors above."
  exit 1
fi

echo "[ BACKEND ] Ready."
echo ""

# ── Step 5: Show status ───────────────────────────────────────────────────────
HEALTH=$(curl -s http://127.0.0.1:8000/health 2>/dev/null)
MODEL=$(echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('model','unknown'))" 2>/dev/null)
DB=$(echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('db_backend','unknown'))" 2>/dev/null)
LLM_OK=$(echo "$HEALTH" | python3 -c "import json,sys; d=json.load(sys.stdin); print('YES' if d.get('llm_configured') else 'NO - add GEMINI_API_KEY to .env')" 2>/dev/null)

echo "  Model    : $MODEL"
echo "  DB       : $DB"
echo "  LLM ready: $LLM_OK"
echo ""

# ── Step 6: Launch Streamlit (opens browser automatically) ────────────────────
echo "[ APP ] Opening in browser at http://localhost:8501 ..."
echo "[ APP ] Close this window to stop everything."
echo ""
.venv/bin/streamlit run app/frontend/app.py \
  --server.headless false \
  --browser.gatherUsageStats false
