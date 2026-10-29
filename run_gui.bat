@echo off
setlocal
rem ------------------------------------------------------------------
rem Agent Hero web UI - no-console launcher (v1.3.0)
rem Starts the FastAPI host with pythonw.exe (no console window),
rem then opens http://127.0.0.1:8765 in your default browser.
rem Run from the agenthero folder (the one containing main.py and plugins\).
rem ------------------------------------------------------------------

set PYW=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe
if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe
if not defined PYW where py >nul 2>nul && set PYW=py -3

if not defined PYW (
    echo ERROR: pythonw.exe not found. Install Python with: winget install -p Microsoft.Python.3.12
    exit /b 1
)

rem "start """ launches the host detached from any console window.
start "" "%PYW%" main.py serve --port 8765
timeout /t 2 >nul
start "" http://127.0.0.1:8765
exit /b 0
