@echo off
setlocal
"%~dp0ReachAssetExport.exe" --mcc "D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection" --out "%~dp0." --effects
if errorlevel 1 echo Collection failed. Keep the error above for troubleshooting.
pause
