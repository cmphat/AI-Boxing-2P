@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo [AI BOXING 3D] Installing Python 3.11 environment...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 required. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 (
  echo Unable to create virtual environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-3d.txt
if errorlevel 1 (
  echo Library installation failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" download_model.py
if errorlevel 1 (
  echo Model download failed.
  pause
  exit /b 1
)
echo Installation finished. Run run_3d.bat
pause
