#!/bin/bash
# Double-click launcher (macOS) for the Turtlemint NL-SQL tool.
# Sets up everything on first run, then starts backend + UI and opens the browser.

cd "$(dirname "$0")" || exit 1

# First-run setup
if [ ! -d ".venv" ]; then
  echo "First run: creating virtual environment and installing dependencies..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

# Seed dummy data if the store is missing
if [ ! -d "app/data/store/chdb" ]; then
  echo "Seeding dummy data..."
  .venv/bin/python -m app.data.seed
fi

# Start the backend
echo "Starting backend on http://127.0.0.1:8000 ..."
.venv/bin/uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'echo "Stopping..."; kill $BACKEND_PID 2>/dev/null' EXIT

# Wait until the backend is ready
for _ in $(seq 1 20); do
  curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 0.5
done

# Start the UI (Streamlit opens the browser automatically). Closing it stops the backend.
echo "Opening the app in your browser..."
.venv/bin/streamlit run app/frontend/app.py
