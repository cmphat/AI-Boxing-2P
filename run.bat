@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Chua cai dat. Hay chay setup.bat truoc.
    pause
    exit /b 1
)

echo Dang khoi dong Y8 Boxing Controller - ban moi...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo Chuong trinh gap loi. Xem thong bao ben tren.
    pause
)
