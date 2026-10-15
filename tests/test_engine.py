import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_convert_html(tmp_path):
    src = tmp_path / "a.html"
    src.write_text("<h1>Hi</h1><p>some <b>bold</b></p>", encoding="utf-8")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({}), encoding="utf-8")
    out = tmp_path / "out.md"
    subprocess.run([sys.executable, str(ROOT / "main.py"), "--convert", str(cfg), str(out), str(src)],
                   check=True, timeout=180)
    text = out.read_text(encoding="utf-8")
    assert "# Hi" in text and "**bold**" in text


def test_batch_reports_failure(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([[str(tmp_path / "missing.pdf"), str(tmp_path / "x.md")]]), encoding="utf-8")
    p = subprocess.run([sys.executable, str(ROOT / "main.py"), "--convert-batch", str(cfg), str(jobs)],
                       capture_output=True, text=True, timeout=180)
    assert '"ok": false' in p.stdout
