@echo off
cd /d "%~dp0"
title LeadGen - Custom Crawl
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" custom_crawl.py %*
pause
