# Changelog

## Unreleased
- Fixed: access violation when importing onnxruntime after PyQt5. PyQt5's wheel bundles an old MSVC runtime (14.26); `fix_qt_runtime.bat` renames those DLLs so the newer system runtime is used. `run.bat` and `build.bat` call it, and the PyInstaller bundle ships only the newer runtime.
- `fix_qt_runtime.bat` locates PyQt5 through the active Python, so it also works outside `.venv`.
- Added GitHub Actions CI (Windows, Python 3.13 and 3.14).

## 0.1.0
- Initial release: Convert, Batch and Settings pages with Fluent Design UI.
- Conversion runs in a child process to avoid an onnxruntime/PyQt5 crash on Windows.
- Crash log at `%USERPROFILE%\MarkItDownGUI-crash.log`.
- PyInstaller build script.
