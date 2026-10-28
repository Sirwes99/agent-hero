@echo off
setlocal
rem ------------------------------------------------------------------
rem Agent Hero GUI - no-console launcher (v1.2.0)
rem Run from the agenthero folder (the one containing gui\app.py and plugins\)
rem Uses pythonw.exe so NO black console window stays open behind the app.
rem ------------------------------------------------------------------

set PYW=
if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe
if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe
if not defined PYW where py >nul 2>nul && set PYW=py -3

if not defined PYW (
    echo ERROR: pythonw.exe not found. Install Python with: winget install -p Microsoft.Python.3.12
    exit /b 1
)

rem "start """ launches the GUI detached from any console window.
start "" "%PYW%" gui\app.py
exit /b 0
