@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo AI BOXING - SETUP CONTROLLER V2
echo ============================================================

py -3.11 --version > nul 2>&1
if errorlevel 1 (
    echo Python 3.11 64-bit chua duoc cai dat.
    echo Tai tai: https://www.python.org/downloads/
    echo Khi cai dat hay tick Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Khong tao duoc virtual environment.
        pause
        exit /b 1
    )
)

echo [1/3] Update pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [2/3] Install packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Loi cai thu vien. Kiem tra Internet va Python 3.11 64-bit.
    pause
    exit /b 1
)

echo [3/3] Download Pose Landmarker FULL...
".venv\Scripts\python.exe" download_model.py
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo SETUP HOAN TAT. Chay run.bat.
pause
