@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay setup.bat truoc.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
pause
