@echo off
setlocal
"%~dp0ReachRepair.exe" --game "%~dp0."
if errorlevel 1 echo Repair failed. Keep the error above for troubleshooting.
pause
