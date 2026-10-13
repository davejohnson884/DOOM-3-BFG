@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  "%~dp0ReachRBDoomPack.exe"
) else (
  "%~dp0ReachRBDoomPack.exe" "%~1"
)
if errorlevel 1 (
  echo Keep the error above for troubleshooting.
)
pause
