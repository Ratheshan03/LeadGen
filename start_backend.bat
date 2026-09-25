@echo off
cd /d "%~dp0"
title LeadGen backend (keep this window open)
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
echo Keep this window open while you crawl. Close it (or press Ctrl+C) to stop the backend.
echo.
".venv\Scripts\python.exe" -m backend
pause
