@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo AI BOXING - Y8 POSE CONTROLLER - WINDOWS SETUP
echo ============================================================

py -3.11 --version > nul 2>&1
if errorlevel 1 (
    echo Khong tim thay Python 3.11 64-bit.
    echo Cai Python 3.11 va tick Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Tao virtual environment that bai.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai thu vien that bai.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" download_model.py
if errorlevel 1 (
    echo Tai model MediaPipe that bai.
    pause
    exit /b 1
)

echo.
echo CAI DAT HOAN TAT.
echo Chay run_y8_controller.bat de bat dau.
pause
