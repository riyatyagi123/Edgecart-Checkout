@echo off
title Grab and Go - AI Smart Retail Checkout
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
echo ===================================================
echo     STARTING GRAB ^& GO SMART RETAIL SYSTEM
echo ===================================================
echo First start downloads the CLIP model (~340 MB) into models\clip
start "" http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
