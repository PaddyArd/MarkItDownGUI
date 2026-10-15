# Architecture

```
main.py     GUI (FluentWindow + Convert / Batch / Settings pages); also the child-process entry point
core.py     Settings (QSettings), QThread workers, child-process launching, crash reporting
engine.py   Qt-free conversion code that wraps markitdown
```

## Why a separate process?

`markitdown` loads `magika`, which loads `onnxruntime`. On Windows, importing `onnxruntime` in a process
that already loaded PyQt5 can crash with an access violation (seen on Python 3.14). To avoid it, the GUI never
imports markitdown. It re-launches itself:

```
python main.py --convert <cfg.json> <out.md> <source>
python main.py --convert-batch <cfg.json> <jobs.json>
```

`main.py` checks for these flags **before** importing any Qt module and hands over to `engine.cli()`.
The child writes its result to a temp file; the parent reads it. A native crash only kills the child, and the
parent reports the exit code and stderr (with `faulthandler` enabled in the child).

In a PyInstaller build `sys.executable` is the app itself, so the same flags work (`core.child_cmd`).

## Flow

1. UI collects the source and calls `SingleWorker` / `BatchWorker` (QThreads).
2. Worker writes the current settings to a temp `cfg.json` and runs the child.
3. Results return through Qt signals; the UI updates the preview or table.
4. Batch mode uses one child per file, so a failure is isolated to that file and Cancel can kill the child.

## Preview safeguards

Control characters (e.g. PDF form feeds) are stripped from output, and the rendered preview is capped at
200,000 characters. The raw tab and Save always contain the full text.
