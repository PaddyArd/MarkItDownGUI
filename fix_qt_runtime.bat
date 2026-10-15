@echo off
REM PyQt5's wheel ships an old MSVC runtime (14.26). If Qt loads first, onnxruntime
REM (used by markitdown via magika) crashes with an access violation. Move the old
REM DLLs aside so the newer system runtime (VC++ 2015-2022 redistributable) is used.
set QTBIN=%~dp0.venv\Lib\site-packages\PyQt5\Qt5\bin
for %%f in (msvcp140 msvcp140_1 msvcp140_2 vcruntime140 vcruntime140_1 concrt140) do (
  if exist "%QTBIN%\%%f.dll" move /y "%QTBIN%\%%f.dll" "%QTBIN%\%%f.dll.old" >nul
)
