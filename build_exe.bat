@echo off
REM Agent Hero - build a standalone Windows EXE (PyInstaller)
REM Output: dist\agent_hero\agent_hero.exe

where python >nul 2>nul
if errorlevel 1 (
    echo Installing Python via winget...
    winget install -p Microsoft.Python.3.12
)

python -m pip install pyinstaller
%LOCALAPPDATA%\Programs\Python\Python312\python.exe -m pip install pyinstaller
pyinstaller --onefile --name agent_hero main.py ^
  --add-data "agenthero;agenthero" ^
  --add-data "plugins;plugins" ^
  --add-data "config.json;."

echo Done. EXE at dist\agent_hero\agent_hero.exe
