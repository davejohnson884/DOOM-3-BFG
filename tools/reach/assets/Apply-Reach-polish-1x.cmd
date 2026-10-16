@echo off
setlocal
echo Close Doom before switching material profiles.
"%~dp0ReachPolish.exe" --game "%~dp0." --scale 1 --lighting pbr
if errorlevel 1 echo Update failed. Keep the error above for troubleshooting.
pause
