"""Qt-free conversion engine. Runs in a child process so native crashes can't kill the GUI."""
import json, re, sys

_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # form feeds etc. from PDFs


def build_converter(cfg: dict):
    from markitdown import MarkItDown

    kwargs = {"enable_plugins": bool(cfg.get("plugins"))}
    if cfg.get("docintel"):
        kwargs["docintel_endpoint"] = cfg["docintel"]
    if cfg.get("openai_key"):
        from openai import OpenAI

        kwargs["llm_client"] = OpenAI(api_key=cfg["openai_key"])
        kwargs["llm_model"] = cfg.get("llm_model") or "gpt-4o"
    return MarkItDown(**kwargs)


def convert_text(md, source: str) -> str:
    result = md.convert(source.strip())
    text = getattr(result, "markdown", None) or result.text_content
    return _CTRL.sub("", text)


def cli(argv):
    """--convert <cfg.json> <out.md> <source> [<source>...]  (one source for single mode).
    Batch mode: --convert-batch <cfg.json> <jobs.json>; prints one JSON line per file."""
    import faulthandler
    faulthandler.enable(sys.stderr)
    if argv[0] == "--convert":
        cfg = json.load(open(argv[1], encoding="utf-8"))
        text = convert_text(build_converter(cfg), argv[3])
        open(argv[2], "w", encoding="utf-8").write(text)
    else:  # --convert-batch
        cfg = json.load(open(argv[1], encoding="utf-8"))
        jobs = json.load(open(argv[2], encoding="utf-8"))  # [[source, target], ...]
        md = build_converter(cfg)
        for i, (src, dst) in enumerate(jobs):
            try:
                text = convert_text(md, src)  # convert first: a failure must not leave an empty .md
                open(dst, "w", encoding="utf-8").write(text)
                print(json.dumps({"i": i, "ok": True, "msg": dst}), flush=True)
            except Exception as e:
                print(json.dumps({"i": i, "ok": False, "msg": f"{type(e).__name__}: {e}"}), flush=True)
