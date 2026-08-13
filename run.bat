@echo off
cd /d "%~dp0"
echo Installing/checking requirements...
pip install -r requirements.txt >nul 2>&1
echo.
echo Starting Discord member export...
echo.
python export_members.py
echo.
pause
