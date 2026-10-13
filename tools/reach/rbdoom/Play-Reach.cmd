@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0RBDoom3BFG.exe" (
  echo Extract this mod into the folder containing your released RBDoom3BFG.exe.
  pause
  exit /b 1
)
if not exist "%~dp0reach\zzz_reach_ar.pk4" (
  echo The reach folder is missing. Extract the complete private mod ZIP here.
  pause
  exit /b 1
)
start "" /D "%~dp0" "%~dp0RBDoom3BFG.exe" +set fs_game reach
