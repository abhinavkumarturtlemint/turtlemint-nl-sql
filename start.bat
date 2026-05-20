@echo off
REM Double-click launcher (Windows) for the Turtlemint NL-SQL tool.
REM Note: chdb may require WSL on native Windows; on macOS use start.command instead.

cd /d "%~dp0"

if not exist ".venv" (
  echo First run: creating virtual environment and installing dependencies...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)

if not exist "app\data\store\chdb" (
  echo Seeding dummy data...
  .venv\Scripts\python -m app.data.seed
)

echo Starting backend on http://127.0.0.1:8000 ...
start "NL-SQL Backend" .venv\Scripts\uvicorn app.backend.main:app --host 127.0.0.1 --port 8000

timeout /t 4 /nobreak >nul

echo Opening the app in your browser...
.venv\Scripts\streamlit run app\frontend\app.py
