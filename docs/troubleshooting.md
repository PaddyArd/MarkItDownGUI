# Troubleshooting

Errors are appended to `%USERPROFILE%\MarkItDownGUI-crash.log`
(Win+R, then `%USERPROFILE%\MarkItDownGUI-crash.log`).

## "Converter process crashed (exit code 0xc0000005)"

An access violation inside a native library. Check the log for the Python stack.

**Known cause: an outdated MSVC runtime from PyQt5.** The PyQt5 wheel ships its own copy of the
Microsoft C++ runtime (`msvcp140.dll` and related files, version 14.26) in `.venv\Lib\site-packages\PyQt5\Qt5\bin`.
`onnxruntime` (loaded by markitdown via `magika`) needs a newer one. Windows loads a DLL only once per process,
so if PyQt5 is imported first, its old runtime is used for everything and `onnxruntime` crashes. Quick check:

```bat
.venv\Scripts\python -c "import PyQt5.QtCore; import onnxruntime; print('OK')"
```

**Fix:** `fix_qt_runtime.bat` renames PyQt5's old runtime DLLs to `*.dll.old` so the newer system runtime
(VC++ 2015-2022 Redistributable, x64) is used. The newer runtime is backward-compatible with Qt. `run.bat` and
`build.bat` call it after every `pip install`. If you install packages manually, run it yourself afterwards.
A built exe bundles the newer runtime in `_internal\`, so end users don't need the redistributable.

The same crash also breaks `build.bat`, with `SubprocessDiedError: Isolated subprocess crashed while importing
package 'magika.types'`. PyInstaller's analysis step imports PyQt5 before `onnxruntime`. Same fix.

The app also converts in a child process that never imports Qt, so a crash in a converter can't take the GUI down.

If you still see the crash:

1. Run the quick check above. If it fails, make sure the Visual C++ Redistributable (x64) is installed and
   up to date, then re-run `fix_qt_runtime.bat`.
2. Test markitdown on its own:
   ```bat
   .venv\Scripts\activate
   python -X faulthandler -c "from markitdown import MarkItDown; print(MarkItDown().convert(r'C:\path\file.pdf').markdown[:300])"
   ```

## The log shows old code paths / fixes seem ignored

Delete the log, re-run `run.bat`, and rebuild with `build.bat` if you use the `.exe`. A previously built
`dist` folder keeps the old code.

## A format is not converted / missing dependency error

Install the extras: `pip install "markitdown[all]"`. Audio transcription needs network access; YouTube and
URL inputs need internet.

## Build problems

If the built exe reports a missing module, add `--hidden-import <module>` to `build.bat`.

You can ignore the build warning `Failed to collect submodules for 'openai.lib.streaming.agents'`.
That module isn't used.
