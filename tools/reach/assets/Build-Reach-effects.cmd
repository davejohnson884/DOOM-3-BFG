@echo off
setlocal
"%~dp0ReachEffectsConvert.exe" --game "C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition" --out "%~dp0reach\zzzzzzzzzz_reach_effects.pk4"
if errorlevel 1 echo Effects conversion failed. Keep the error above for troubleshooting.
pause
