# Handoff: MarkItDown GUI

Project folder: `D:\Projects\Development\MarkitDownGUI` (Windows, Python venv in `.venv`, Python 3.14.7)

## Goal
Fluent Design (Microsoft) desktop GUI for [microsoft/markitdown](https://github.com/microsoft/markitdown).

## Decisions made with the user
- Stack: Python + PyQt5 + PyQt-Fluent-Widgets (1.11.3). Not WinUI/Flet.
- Features: single file/URL/YouTube convert with live preview (rendered + raw), batch (files/folders), settings (theme, output folder, plugins, Azure Doc Intelligence, OpenAI key/model).
- PyInstaller build script (`build.bat`), output `dist\MarkItDown\MarkItDown.exe` (~316 MB folder build).
- User preferences: brief explanations, ask clarifying questions before detailed answers, be critical.

## Current code layout
- `main.py`: GUI. **Before any Qt import** it checks for `--convert` / `--convert-batch` argv and hands off to `engine.cli()` (child-process mode).
- `core.py`: QSettings, `SingleWorker`/`BatchWorker` QThreads that launch the child process (`child_cmd`), `describe_crash`, `output_path` (never overwrites; adds ` (n)`).
- `engine.py`: Qt-free wrapper around markitdown; strips control chars (PDF form feeds); `faulthandler` enabled. Batch mode converts before opening the output file, so failures leave no empty `.md`.
- `fix_qt_runtime.bat`: moves PyQt5's outdated MSVC runtime DLLs aside (see below). Called by `run.bat` and `build.bat` after `pip install`.
- `run.bat`, `build.bat`, `requirements.txt`, `requirements-dev.txt`, `tests/test_engine.py`, `README.md`, `docs/architecture.md`, `docs/troubleshooting.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` (MIT), `.gitignore`.
- Preview: rendered tab capped at 200,000 chars; Markdown tab and Save have full text.
- Errors append to `%USERPROFILE%\MarkItDownGUI-crash.log`.

## Crash on conversion: RESOLVED (2026-10-15)
Symptom: `Windows fatal exception: access violation` while importing `onnxruntime` (via `magika` via `markitdown`) in the GUI process. The same crash made PyInstaller fail with `SubprocessDiedError ... importing package 'magika.types'`.

**Root cause:** the PyQt5 wheel bundles an old MSVC runtime (`msvcp140*.dll`, `vcruntime140*.dll`, `concrt140.dll`, version 14.26) in `PyQt5\Qt5\bin`. `onnxruntime` needs a newer runtime (system has 14.51). Windows loads the DLL once per process, so the import order decides which version wins:
- `import PyQt5.QtCore; import onnxruntime` → segfault
- `import onnxruntime; import PyQt5.QtCore` → OK

Python 3.14 was not the cause.

**Fix:** `fix_qt_runtime.bat` renames those DLLs to `*.dll.old`, so the system's newer runtime is used. The runtime is backward-compatible with Qt. The child-process conversion is kept for crash isolation.

**Verified on Windows:**
- `pytest`: 2 tests pass.
- Source `main.py --convert` on `D:\Manuals\London Electronics\Analogue_Output_INT4.pdf`: OK (16 KB Markdown).
- `SingleWorker` and `BatchWorker` run from a process with PyQt5 and qfluentwidgets loaded: OK. A missing file is reported as an error.
- `build.bat` builds successfully. The bundle has only the 14.51 runtime in `_internal\`, so end users don't need the VC++ redistributable.
- Exe `--convert` and `--convert-batch` (stdout over a pipe) both work on the PDF.
- The GUI exe and `main.py` both start and stay up. Nobody has clicked through either window.

## Not done
- Manual click-through of the GUI (exe and source): convert via the UI, preview tabs, Save, batch page.
- Untested: Settings page, URL/YouTube input, Azure/OpenAI options.

## Done since
- GitHub repo created: https://github.com/PaddyArd/MarkItDownGUI (branch `main`, signed commits).
- CI added: `.github/workflows/ci.yml` runs on `windows-latest` with Python 3.13/3.14: `pip install -r requirements-dev.txt`, `fix_qt_runtime.bat`, `pytest -q`.
- `fix_qt_runtime.bat` now finds PyQt5 through the active `python` instead of `%~dp0.venv`, so it works in CI and still works from `run.bat`/`build.bat` (they activate the venv first). It exits with an error if PyQt5 can't be imported.

## Things to watch
- `fix_qt_runtime.bat` must re-run after any reinstall or upgrade of PyQt5. Dev machines need the VC++ 2015-2022 x64 redistributable.
- Licensing: PyQt5 is GPLv3/commercial and PyQt-Fluent-Widgets is GPLv3 for non-commercial (commercial licence available). Flagged in the README; the author name in LICENSE is a placeholder.
- OpenAI key is stored unencrypted in the registry (`HKCU\Software\MarkItDownGUI`).
- Harmless build warning: `Failed to collect submodules for 'openai.lib.streaming.agents'`.
- The exe folder is 316 MB. Consider excluding unused heavy packages (e.g. pandas/numpy extras) if size matters.

## Suggested next steps
1. Click through the GUI exe: single convert + preview + Save, batch, settings, URL/YouTube.
