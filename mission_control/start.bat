@echo off
title Mission Control
cd /d "%~dp0\.."
call venv\Scripts\activate.bat
python -m mission_control.start_tunnel
pause
