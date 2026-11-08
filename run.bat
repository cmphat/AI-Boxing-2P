@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong Python. Dang tu cai dat...
    call setup.bat
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -c "import cv2, mediapipe, PIL, pynput" > nul 2>&1
if errorlevel 1 (
    echo Thieu thu vien. Dang cai bo phu thuoc...
    call setup.bat
    if errorlevel 1 exit /b 1
)

if not exist "assets\pose_landmarker_lite.task" (
    echo Dang tai model Pose LITE...
    ".venv\Scripts\python.exe" download_model.py
    if errorlevel 1 (
        pause
        exit /b 1
    )
)

echo Dang mo AI Boxing va tu dong mo Y8...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo Controller gap loi. Chup man hinh loi va gui lai.
    pause
)
