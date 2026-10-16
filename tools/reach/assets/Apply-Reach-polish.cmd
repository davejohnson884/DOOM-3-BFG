@echo off
setlocal
echo Close Doom before applying this material and effects update.
"%~dp0ReachPolish.exe" --game "%~dp0." --scale 2 --lighting pbr
if errorlevel 1 echo Update failed. Keep the error above for troubleshooting.
pause
