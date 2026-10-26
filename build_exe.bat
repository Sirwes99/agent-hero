@echo off
setlocal
rem ------------------------------------------------------------------
rem Agent Hero GUI - PyInstaller build script
rem Run from the agentforge folder (the one containing gui\app.py and plugins\)
rem Output: dist\agent_hero\agent_hero.exe
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

echo.
echo Done. Run: dist\agent_hero\agent_hero.exe
