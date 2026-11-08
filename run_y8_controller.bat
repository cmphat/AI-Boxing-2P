@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua co moi truong .venv. Hay chay setup_y8.bat truoc.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" y8_controller.py
pause
