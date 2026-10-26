@echo off
setlocal
cd /d "%~dp0"

REM --- Bootstrap Python if missing (uses winget; falls back to a message) ---
where python >nul 2>nul
if errorlevel 1 (
    echo [agent-hero] Python not found. Installing via winget...
    winget install -q Python.Python.3.14 --exact --silent --accept-source-agreements
    if errorlevel 1 (
        echo [agent-hero] Could not auto-install Python. Install it from https://www.python.org and re-run this script.
        exit /b 1
    )
)

REM --- Install dependencies ---
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [agent-hero] Failed to install dependencies. Check your internet connection.
    exit /b 1
)

echo.
echo ============================================================
echo  Agent Hero is running: http://127.0.0.1:8765
echo  Web UI at that URL, or point any OpenAI-compatible client
echo  (e.g. LM Studio) at http://127.0.0.1:8765/v1/chat/completions
echo ============================================================
python main.py serve --port 8765
