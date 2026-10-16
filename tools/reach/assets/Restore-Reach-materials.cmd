@echo off
setlocal
echo Close Doom before restoring the working materials.
"%~dp0ReachMaterialRestore.exe" --game "%~dp0."
set "reach_restore_result=%errorlevel%"
if not "%reach_restore_result%"=="0" echo Restore failed. Keep the error above for troubleshooting.
pause
exit /b %reach_restore_result%
