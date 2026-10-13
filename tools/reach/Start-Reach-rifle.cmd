@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-playtest.ps1" -ReachRifle
if errorlevel 1 echo Rifle playtest failed. Keep the error above for troubleshooting.
pause
