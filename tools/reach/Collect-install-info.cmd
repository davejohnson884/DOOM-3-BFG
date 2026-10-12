@echo off
setlocal
rem The execution policy override applies only to this PowerShell process.
rem This script inventories files; it does not change Steam game files.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0collect-install-info.ps1"
if errorlevel 1 (
  echo Collection failed. Keep the error above for troubleshooting.
) else (
  echo Send the reach-install-info JSON file from this folder to the project chat.
)
pause
