@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-playtest.ps1" -SingleThreaded -Diagnostics %*
if errorlevel 1 echo Diagnostic setup failed. Keep the error above for troubleshooting.
pause
