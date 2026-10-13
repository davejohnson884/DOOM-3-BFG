@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-playtest.ps1" -StockCombat -Diagnostics %*
if errorlevel 1 echo Baseline setup failed. Keep the error above for troubleshooting.
pause
