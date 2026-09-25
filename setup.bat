@echo off
setlocal
cd /d "%~dp0"
title LeadGen setup
echo.
echo  LeadGen setup
echo  =============
echo.

set "PY="
for %%V in (3.12 3.11 3.13 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo  Python 3.10 - 3.13 was not found.
    echo  Install Python 3.12 from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^)
    echo  and run setup.bat again.
    goto :fail
)
echo  Using: %PY%

if not exist ".venv\Scripts\python.exe" (
    echo  Creating the Python environment in .venv ...
    %PY% -m venv .venv || goto :fail
)
echo  Installing packages - this takes a few minutes the first time ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet || goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet || goto :fail

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo  Created .env - open it and paste your Google API key after GOOGLE_API_KEYS=
) else (
    echo  .env already exists - left unchanged.
)

echo.
echo  Setup complete.
echo  Next: 1^) put your Google API key in .env   2^) double-click start_backend.bat
echo        3^) double-click custom_crawl.bat or start_dashboard.bat
echo.
pause
exit /b 0

:fail
echo.
echo  Setup did not finish - see the messages above.
pause
exit /b 1
