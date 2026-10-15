@echo off
REM PyQt5's wheel ships an old MSVC runtime (14.26). If Qt loads first, onnxruntime
REM (used by markitdown via magika) crashes with an access violation. Move the old
REM DLLs aside so the newer system runtime (VC++ 2015-2022 redistributable) is used.
REM PyQt5 is located through the active "python" (the venv in run.bat/build.bat, the
REM runner's Python in CI).
setlocal
set QTBIN=
for /f "delims=" %%d in ('python -c "import os, PyQt5; print(os.path.dirname(PyQt5.__file__))"') do set "QTBIN=%%d\Qt5\bin"
if not defined QTBIN (
  echo fix_qt_runtime: PyQt5 not found for the active python 1>&2
  exit /b 1
)
for %%f in (msvcp140 msvcp140_1 msvcp140_2 vcruntime140 vcruntime140_1 concrt140) do (
  if exist "%QTBIN%\%%f.dll" move /y "%QTBIN%\%%f.dll" "%QTBIN%\%%f.dll.old" >nul
)
endlocal
