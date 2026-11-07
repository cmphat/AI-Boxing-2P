@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Run setup_3d.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m solo3d.main --demo
pause
