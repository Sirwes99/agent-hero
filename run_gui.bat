@echo off
setlocal
rem ------------------------------------------------------------------
rem Agent Hero web UI launcher (v1.3.1)
rem Starts the no-console FastAPI host and opens http://127.0.0.1:8765
rem in your default browser once it is actually ready.
rem
rem Preferred path: dist\AgentHeroHost.exe  (frozen, self-contained,
rem   no Python required at runtime, no console window). Built by build_exe.bat.
rem Fallback: pythonw source mode if the exe has not been built yet.
rem ------------------------------------------------------------------

cd /d %~dp0

if exist "%~dp0dist\AgentHeroHost.exe" (
    start "" "%~dp0dist\AgentHeroHost.exe"
) else (
    set PYW=
    if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe
    if not defined PYW if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe
    if not defined PYW where py >nul 2>nul && set PYW=py -3

    if not defined PYW (
        echo ERROR: AgentHeroHost.exe was not found and pythonw.exe is unavailable.
        echo Build the exe first with build_exe.bat, or install Python: winget install -p Microsoft.Python.3.12
        exit /b 1
    )

    start "" "%PYW%" host_launcher.py
)

rem Poll up to 60 s (frozen-exe extraction can take ~45 s on slower machines).
rem PowerShell exits 0 as soon as port 8765 is LISTENING, else 1 after the loop.
powershell -NoProfile -Command "$found=$false; for($i=0;$i -lt 60;$i++){ $l = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if($l){ exit 0 }; Start-Sleep -Milliseconds 1000 }; exit 1"
if errorlevel 1 goto fail

start "" http://127.0.0.1:8765
exit /b 0

:fail
echo ERROR: the Agent Hero server did not start within 60 seconds.
echo If you are using the frozen exe, make sure dist\AgentHeroHost.exe is up to date (run build_exe.bat).
pause
exit /b 1
