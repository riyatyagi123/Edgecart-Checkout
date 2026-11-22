@echo off
title Grab and Go - Edge Shelf Node
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
REM Use --source 0 for the webcam, or a video file path.
python edge\edge_node.py --source sample_videos\shop_shelf.mp4 --server http://127.0.0.1:8000 --node-id shelf-01
pause
