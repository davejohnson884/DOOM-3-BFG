@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-rifle-script.ps1"
if errorlevel 1 (
  echo Keep the error above for troubleshooting.
)
pause
