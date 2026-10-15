@echo off
REM Builds dist\MarkItDown\MarkItDown.exe  (run from this folder)
python -m venv .venv || exit /b 1
call .venv\Scripts\activate
pip install -r requirements.txt pyinstaller || exit /b 1
call "%~dp0fix_qt_runtime.bat"
pyinstaller --noconfirm --windowed --name MarkItDown ^
  --collect-all markitdown --collect-all magika --collect-all qfluentwidgets ^
  --collect-submodules openai --hidden-import engine main.py || exit /b 1
echo Done: dist\MarkItDown\MarkItDown.exe
