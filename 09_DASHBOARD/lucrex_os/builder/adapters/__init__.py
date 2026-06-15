# builder/adapters/__init__.py
import json, pathlib, subprocess

def _file(src):
    return json.loads(pathlib.Path(src["path"]).read_text())

def _cmd(src):
    out = subprocess.run(src["cmd"], shell=True, capture_output=True, text=True, timeout=20)
    return json.loads(out.stdout)

_ADAPTERS = {"file": _file, "cmd": _cmd}

def load_source(src: dict) -> dict:
    t = src.get("type")
    if t not in _ADAPTERS:
        raise ValueError(f"unknown source type: {t!r}")
    return _ADAPTERS[t](src)
