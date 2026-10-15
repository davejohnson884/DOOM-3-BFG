@echo off
setlocal
"%~dp0ReachArAppearance.exe" --game "C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition"
if errorlevel 1 echo Appearance conversion failed. Keep the error above for troubleshooting.
pause
