@echo off
cd /d "%~dp0"
title LeadGen dashboard (keep this window open)
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)
echo The dashboard opens in your browser at http://127.0.0.1:8501
echo Make sure start_backend.bat is running too. Close this window to stop the dashboard.
echo.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8501"
".venv\Scripts\python.exe" -m streamlit run dashboard\Home.py
pause
