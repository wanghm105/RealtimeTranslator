@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run install.bat first.
  pause
  exit /b 1
)
rem Refuse to launch if another process is using one of the default ports.
powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 18090,8765,8766 }) { exit 1 }"
if errorlevel 1 (
  echo A required port is already in use. No processes were stopped.
  pause
  exit /b 1
)
start "RealtimeTranslator Server" "%~dp0.venv\Scripts\python.exe" "%~dp0realtime_server.py"
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 20;$i++){ try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:18090/health' -UseBasicParsing -TimeoutSec 1; if($r.StatusCode -eq 200){$ok=$true;break} } catch {}; Start-Sleep -Milliseconds 500 }; if(-not $ok){exit 1}"
if errorlevel 1 (
  echo Server did not become ready. Check the server window.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:18090"
start "RealtimeTranslator" "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
echo Close both RealtimeTranslator windows to stop the application.
pause
