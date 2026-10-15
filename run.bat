@echo off
python -m venv .venv 2>nul
call .venv\Scripts\activate
pip install -q -r requirements.txt
call "%~dp0fix_qt_runtime.bat"
python main.py
if errorlevel 1 pause
