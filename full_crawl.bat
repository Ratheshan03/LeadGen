@echo off
cd /d "%~dp0"
title LeadGen - Full Crawl
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" full_crawl.py %*
pause
