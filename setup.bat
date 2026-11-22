@echo off
title Grab and Go - Setup
cd /d "%~dp0"
echo Creating virtual environment...
python -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :error
echo.
echo Setup complete. Run run_app.bat to start the server.
pause
exit /b 0
:error
echo Setup failed. Make sure Python 3.10+ and Git are installed and on PATH.
pause
exit /b 1
