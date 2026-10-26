@echo off
REM Agent Hero - Windows launcher
REM Installs Python via winget if missing, installs deps, starts the host.

where python >nul 2>nul
if errorlevel 1 (
    echo Installing Python via winget...
    winget install -p Microsoft.Python.3.12
)

python -m pip install -r requirements.txt
python main.py serve --port 8765
