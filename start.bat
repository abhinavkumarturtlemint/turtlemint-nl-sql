@echo off
REM =============================================================================
REM  Turtlemint NL-SQL -- Windows double-click launcher
REM  Double-click this file to start the full application.
REM  Closes both backend + frontend when you close this window.
REM =============================================================================

cd /d "%~dp0"

echo.
echo   TURTLEMINT NL-SQL  ^|  Plain English -^> ClickHouse
echo.

REM -- Step 1: Create virtual environment on first run -------------------------
if not exist ".venv" (
    echo [ SETUP ] First run detected -- creating virtual environment...
    python -m venv .venv
    echo [ SETUP ] Installing dependencies (this takes ~1 min)...
    .venv\Scripts\python -m pip install --upgrade pip -q
    .venv\Scripts\pip install -r requirements.txt -q
    echo [ SETUP ] Done.
    echo.
)

REM -- Step 2: Verify .env exists ----------------------------------------------
if not exist ".env" (
    echo [ WARNING ] .env file not found!
    echo   Create a file named .env with the following content:
    echo.
    echo   GEMINI_API_KEY=your_key_here
    echo   GEMINI_MODEL=gemini-2.5-flash
    echo   DB_BACKEND=api_duckdb
    echo   OPENMETADATA_GLOSSARY_URL=https://ninja.turtlemintinsurance.com/api/crm/openmetadata/search/glossary
    echo   OPENMETADATA_SAMPLE_URL=https://ninja.turtlemintinsurance.com/api/crm/openmetadata/pii_latest_sample_data
    echo.
    pause
)

REM -- Step 3: Start the FastAPI backend in a new window -----------------------
echo [ BACKEND ] Starting on http://127.0.0.1:8000 ...
start "Turtlemint NL-SQL Backend" /min cmd /c ".venv\Scripts\uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --log-level warning"

REM -- Step 4: Wait for backend to be ready ------------------------------------
echo [ BACKEND ] Waiting for health check...
set READY=0
for /L %%i in (1,1,30) do (
    if "!READY!"=="0" (
        curl -s http://127.0.0.1:8000/health >nul 2>&1
        if !errorlevel! == 0 (
            set READY=1
        ) else (
            timeout /t 1 /nobreak >nul
        )
    )
)

if "%READY%"=="0" (
    echo [ ERROR ] Backend did not start in time. Check the backend window for errors.
    pause
    exit /b 1
)

echo [ BACKEND ] Ready.
echo.

REM -- Step 5: Launch Streamlit (opens browser automatically) ------------------
echo [ APP ] Opening in browser at http://localhost:8501 ...
echo [ APP ] Close this window to stop the frontend.
echo.
.venv\Scripts\streamlit run app\frontend\app.py --server.headless false --browser.gatherUsageStats false
