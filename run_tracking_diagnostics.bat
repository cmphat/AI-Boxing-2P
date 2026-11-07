@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_3d.bat first.
  pause
  exit /b 1
)
echo ===================================================
echo AI BOXING - TEST 33 POSE LANDMARKS AND X/Z
echo C calibrate ^| S screenshot ^| Q quit
echo Output: motion_log.csv
echo ===================================================
".venv\Scripts\python.exe" -m solo3d.diagnose --record
pause
