@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-playtest.ps1" -SingleThreaded %*
if errorlevel 1 echo Playtest setup failed. Keep the error above for troubleshooting.
pause
