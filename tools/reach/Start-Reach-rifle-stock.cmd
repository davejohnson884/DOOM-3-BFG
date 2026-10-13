@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-playtest.ps1" -ReachRifle -RetailRifle
if errorlevel 1 echo Stock-engine rifle preview failed. Keep the error above for troubleshooting.
pause
