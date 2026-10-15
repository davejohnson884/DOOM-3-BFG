@echo off
setlocal
"%~dp0ReachArAppearance.exe" --game "C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition" --out "%~dp0reach\zzzzzzzz_reach_appearance.pk4"
if errorlevel 1 echo Appearance conversion failed. Keep the error above for troubleshooting.
pause
