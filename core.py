"""Settings + background workers. Conversion runs in a separate process."""
from __future__ import annotations

import json, os, subprocess, sys, tempfile
from pathlib import Path
from PyQt5.QtCore import QSettings, QThread, pyqtSignal

APP_ORG, APP_NAME = "MarkItDownGUI", "MarkItDownGUI"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def settings() -> QSettings:
    return QSettings(APP_ORG, APP_NAME)


def current_config() -> dict:
    s = settings()
    return {"plugins": s.value("plugins", False, bool),
            "docintel": s.value("docintel", "", str).strip(),
            "openai_key": s.value("openai_key", "", str).strip(),
            "llm_model": s.value("llm_model", "gpt-4o", str)}


def child_cmd(*args: str) -> list[str]:
    """Command to re-launch this app in engine mode (works from source and from PyInstaller)."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, str(Path(__file__).with_name("main.py")), *args]


def describe_crash(code: int, stderr: str) -> str:
    tail = "\n".join(stderr.strip().splitlines()[-12:])
    hint = f"Converter process crashed (exit code {code & 0xFFFFFFFF:#x})." if code < 0 or code > 255 \
        else f"Converter process failed (exit code {code})."
    log = Path.home() / "MarkItDownGUI-crash.log"
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"--- {hint}\n{stderr}\n")
    except Exception:
        pass
    return f"{hint}\n{tail}" if tail else hint


def output_path(src: str, out_dir: str) -> Path:
    p = Path(src)
    folder = Path(out_dir) if out_dir else p.parent
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (p.stem + ".md")
    n = 1
    while target.exists():  # never overwrite
        target = folder / f"{p.stem} ({n}).md"
        n += 1
    return target


class SingleWorker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, source: str, parent=None):
        super().__init__(parent)
        self.source = source

    def run(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, out = os.path.join(tmp, "cfg.json"), os.path.join(tmp, "out.md")
            json.dump(current_config(), open(cfg, "w", encoding="utf-8"))
            try:
                p = subprocess.run(child_cmd("--convert", cfg, out, self.source),
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", creationflags=NO_WINDOW)
            except Exception as e:
                return self.failed.emit(f"{type(e).__name__}: {e}")
            if p.returncode != 0 or not os.path.exists(out):
                return self.failed.emit(describe_crash(p.returncode, p.stderr))
            self.done.emit(open(out, encoding="utf-8").read())


class BatchWorker(QThread):
    progress = pyqtSignal(int, bool, str)  # row, ok, message
    finished_all = pyqtSignal(int, int)

    def __init__(self, files: list[str], out_dir: str, parent=None):
        super().__init__(parent)
        self.files, self.out_dir = files, out_dir
        self._cancel = False
        self._proc = None

    def cancel(self):
        self._cancel = True
        if self._proc:
            self._proc.kill()

    def run(self):
        ok_n = fail_n = 0
        with tempfile.TemporaryDirectory() as tmp:
            cfg = os.path.join(tmp, "cfg.json")
            json.dump(current_config(), open(cfg, "w", encoding="utf-8"))
            for i, f in enumerate(self.files):  # one process per file: a crash only fails that file
                if self._cancel:
                    break
                try:
                    target = output_path(f, self.out_dir)
                    jobs = os.path.join(tmp, "jobs.json")
                    json.dump([[f, str(target)]], open(jobs, "w", encoding="utf-8"))
                    self._proc = subprocess.Popen(child_cmd("--convert-batch", cfg, jobs),
                                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                  text=True, encoding="utf-8", errors="replace",
                                                  creationflags=NO_WINDOW)
                    out, err = self._proc.communicate()
                    line = next((l for l in out.splitlines() if l.startswith("{")), None)
                    res = json.loads(line) if line else None
                    if res and res["ok"]:
                        ok_n += 1
                        self.progress.emit(i, True, res["msg"])
                    else:
                        fail_n += 1
                        self.progress.emit(i, False, res["msg"] if res else
                                           describe_crash(self._proc.returncode, err).splitlines()[0])
                except Exception as e:
                    fail_n += 1
                    self.progress.emit(i, False, f"{type(e).__name__}: {e}")
        self.finished_all.emit(ok_n, fail_n)
