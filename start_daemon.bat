@echo off
cd /d "%~dp0"
echo [1/3] Starting NapCat Docker...
docker compose up -d
echo [2/3] Stopping old daemon...
powershell -Command "Get-CimInstance Win32_Process -Filter \"name like 'python%'\" | Where-Object CommandLine -like '*qq_daemon*' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 2 /nobreak >nul
echo [3/3] Starting daemon...
start /B "" "C:\Program Files\Python314\python.exe" "%~dp0qq_daemon.py"
timeout /t 3 /nobreak >nul
for /f %%i in ('type napcat_data\daemon.pid 2^>nul') do set PID=%%i
if defined PID (
  powershell -Command "if (Get-Process -Id %PID% -ErrorAction SilentlyContinue) { Write-Host [OK] Daemon running (PID %PID%) } else { Write-Host [FAIL] Daemon failed to start! }"
) else (
  echo [FAIL] PID file not found
)
