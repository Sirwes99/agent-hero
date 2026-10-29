@echo off
setlocal
rem ------------------------------------------------------------------
rem Agent Hero - PyInstaller build script (v1.3.1)
rem Builds BOTH executables from the agenthero folder:
rem   1. dist\agent_hero\agent_hero.exe   — windowed Tkinter GUI desktop app
rem   2. dist\AgentHeroHost.exe           — no-console web host launcher
rem      (double-click it: starts http://127.0.0.1:8765 and opens the browser)
rem ------------------------------------------------------------------

set PY=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if not defined PY where py >nul 2>nul && set PY=py -3

if not defined PY (
    echo ERROR: Python not found. Install it with: winget install -p Microsoft.Python.3.12
    exit /b 1
)

echo Using Python: %PY%
%PY% -m pip install --quiet pyinstaller
if errorlevel 1 (
    echo ERROR: could not install PyInstaller.
    exit /b 1
)

rem --- 1. Tkinter GUI exe (windowed desktop app) ---
rem NOTE: "plugins;plugins" keeps the plugins folder intact inside _internal\plugins
%PY% -m PyInstaller --name agent_hero --onedir --noconfirm ^
  --add-data "plugins;plugins" ^
  --add-data "config.json;." ^
  --hidden-import uvicorn --hidden-import fastapi --hidden-import agenthero.server ^
  --collect-all tkinter gui/app.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

rem --- 2. No-console web host exe (AgentHeroHost.exe, single file) ---
%PY% -m PyInstaller --noconfirm --distpath dist agent_hero_host.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo Done. Run either:
echo   dist\agent_hero\agent_hero.exe   (windowed GUI, no Python needed at runtime)
echo   dist\AgentHeroHost.exe           (web UI in your browser, no console window)
