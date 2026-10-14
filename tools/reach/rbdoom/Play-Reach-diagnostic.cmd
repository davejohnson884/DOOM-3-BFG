@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0RBDoom3BFG.exe" (
  echo Extract this update into the folder containing RBDoom3BFG.exe.
  pause
  exit /b 1
)
if not exist "%~dp0reach\zzz_reach_ar.pk4" (
  echo Install the original Reach rifle mod first.
  pause
  exit /b 1
)
if not exist "%~dp0reach\zzzz_reach_switch.pk4" (
  echo Extract the complete Reach switch diagnostic ZIP here.
  pause
  exit /b 1
)
if not exist "%~dp0ReachDebugLog.exe" (
  echo Extract the complete r2 diagnostic ZIP, including ReachDebugLog.exe.
  pause
  exit /b 1
)
echo After closing the game, File Explorer will select Reach-weapon-debug.log.
"%~dp0ReachDebugLog.exe" "%~dp0RBDoom3BFG.exe" "%TEMP%\Reach-weapon-debug.log" +set fs_game reach +set logFileName "%TEMP%\Reach-weapon-switch.log" +set logFile 2 +set g_debugWeapon 1
if errorlevel 1 (
  pause
  exit /b 1
)
if /i "%~1"=="--no-explorer" exit /b 0
if exist "%TEMP%\Reach-weapon-debug.log" explorer.exe /select,"%TEMP%\Reach-weapon-debug.log"
