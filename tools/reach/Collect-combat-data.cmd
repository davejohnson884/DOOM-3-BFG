@echo off
setlocal
rem Read-only extraction of text definitions/scripts to a new private folder.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0collect-combat-data.ps1" -OutputDirectory "%~dp0."
if errorlevel 1 (
  echo Collection failed. Keep the error above for troubleshooting.
) else (
  echo Attach the new reach-combat-data ZIP here privately; do not upload it to GitHub.
)
pause
