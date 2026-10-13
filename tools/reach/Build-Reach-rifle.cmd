@echo off
setlocal
cd /d "%~dp0"
set "reachDonor=%~1"
if not defined reachDonor for /f "delims=" %%D in ('dir /b /ad /o-d "reach-assets-*" 2^>nul') do if not defined reachDonor set "reachDonor=%~dp0%%D"
if not defined reachDonor (
  echo Drag your full reach-assets ZIP or extracted donor folder onto this CMD.
  echo You do not need to collect the game files again.
  pause
  exit /b 1
)
"%~dp0ReachAssetConvert.exe" --donor "%reachDonor%" --bfg "C:\Program Files (x86)\Steam\steamapps\common\DOOM 3 BFG Edition"
if errorlevel 1 (
  echo Conversion failed. Keep the error above for troubleshooting.
) else (
  echo Conversion complete. Start-Reach-rifle-stock.cmd previews them using your installed Steam executable.
)
pause
