@echo off
setlocal
echo Close Doom before disabling the r16 overlay.
"%~dp0ReachPolish.exe" --game "%~dp0." --undo
if errorlevel 1 echo Undo failed. Keep the error above for troubleshooting.
pause
