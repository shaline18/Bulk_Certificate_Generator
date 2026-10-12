@echo off
cd /d "%~dp0"
echo Starting Certify... your browser will open automatically.
echo Keep this window open while you use the app. Close it to stop.
uv run python run.py
pause
