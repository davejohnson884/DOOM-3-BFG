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
echo The log is saved to %TEMP%\Reach-weapon-switch.log
echo After closing the game, File Explorer will select that log for you.
start "" /wait /D "%~dp0" "%~dp0RBDoom3BFG.exe" +set fs_game reach +set logFileName "%TEMP%\Reach-weapon-switch.log" +set logFile 2 +set g_debugWeapon 1
if exist "%TEMP%\Reach-weapon-switch.log" explorer.exe /select,"%TEMP%\Reach-weapon-switch.log"
