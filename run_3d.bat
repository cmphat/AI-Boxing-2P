@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup_3d.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m fps3d.main --mode pvp --sensitivity 1.15
pause
