@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo AI BOXING - CAI DAT BAN Y8 CONTROLLER MOI
echo ============================================================

py -3.11 --version > nul 2>&1
if errorlevel 1 (
    echo Khong tim thay Python 3.11 64-bit.
    echo Cai Python 3.11 tu https://www.python.org/downloads/
    echo Nho tick Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Tao moi truong ao that bai.
        pause
        exit /b 1
    )
)

echo [1/3] Nang cap pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [2/3] Cai thu vien...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai thu vien that bai.
    pause
    exit /b 1
)

echo [3/3] Tai model MediaPipe...
".venv\Scripts\python.exe" download_model.py
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo CAI DAT HOAN TAT. Bam run.bat de mo game.
pause
