from __future__ import annotations

import json
import re
from pathlib import Path

# Stable code names assigned to recurring radio identifiers so the operator can
# follow who is working which call across the whole day (persisted mapping).
_POOL = [
    "RAVEN", "FALCON", "COBRA", "WOLF", "GHOST", "VIPER", "HAWK", "BEAR", "LYNX",
    "ORCA", "TALON", "JACKAL", "PANTHER", "OSPREY", "MAMBA", "RONIN", "SABLE",
    "KESTREL", "BRONCO", "ROOK", "GRYPHON", "BADGER", "CONDOR", "MARLIN", "STAG",
    "HERON", "COYOTE", "DRAKE", "OTTER", "LEOPARD",
]

_DISPATCH = re.compile(r"\b(dispatch|control|county\s*comm|comms?)\b", re.I)
_PHON = ("adam|boy|charlie|david|edward|frank|george|henry|ida|john|king|lincoln|"
         "mary|nora|ocean|paul|queen|robert|sam|tom|union|victor|william|xray|young|zebra")
_UNIT = re.compile(rf"\b(?:unit\s+(\d{{1,3}})|(\d{{1,2}})[-\s]({_PHON})(?:[-\s](\d{{1,3}}))?)\b", re.I)

# Common CA scanner codes -> plain-English event so the operator sees the EVENT.
_CODES = {
    "211": "robbery", "459": "burglary", "415": "disturbance", "5150": "mental-health hold",
    "10851": "stolen vehicle", "242": "battery", "240": "assault", "417": "brandishing",
    "245": "assault w/ weapon", "207": "kidnap", "187": "homicide", "1199": "officer needs help",
    "1198": "meet officer", "20001": "felony hit-run", "20002": "hit-run", "23152": "DUI",
    "1179": "injury collision", "1180": "major-injury collision", "1181": "collision",
    "1125": "traffic hazard", "902": "medical", "104": "acknowledged", "1097": "on scene",
    "CODE3": "lights + siren",
}
_CODE_RE = re.compile(
    r"\b(211|459|415|5150|10851|242|240|417|245|207|187|11-?99|11-?98|20001|20002|"
    r"23152|1179|1180|1181|1125|902|10-?4|10-?97|code\s?3)\b",
    re.I,
)


def code_name(raw: str, base: str | Path) -> str:
    """Stable code name for a radio identifier (persisted to radio_codenames.json)."""
    p = Path(base) / "radio_codenames.json"
    m: dict = {}
    if p.exists():
        try:
            m = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            m = {}
    key = raw.upper().strip()
    if key not in m:
        i = len(m)
        suffix = f"-{i // len(_POOL)}" if i >= len(_POOL) else ""
        m[key] = _POOL[i % len(_POOL)] + suffix
        try:
            p.write_text(json.dumps(m))
        except Exception:  # noqa: BLE001
            pass
    return m[key]


def extract(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Raw speaker/unit ids + (code, label) event codes found in a line."""
    ids: list[str] = []
    if _DISPATCH.search(text):
        ids.append("DISPATCH")
    for mt in _UNIT.finditer(text):
        if mt.group(1):
            ids.append(f"UNIT-{mt.group(1)}")
        elif mt.group(2):
            tail = f"-{mt.group(4)}" if mt.group(4) else ""
            ids.append(f"{mt.group(2)}-{mt.group(3).upper()[:3]}{tail}")
    codes: list[tuple[str, str]] = []
    for m in _CODE_RE.finditer(text):
        norm = m.group(0).upper().replace(" ", "").replace("-", "")
        codes.append((m.group(0).upper(), _CODES.get(norm, "")))
    return list(dict.fromkeys(ids)), list(dict.fromkeys(codes))


def annotate_line(ts_str: str, text: str, base: str | Path) -> str:
    """Format one transcript line: [time] [CODENAMES] text {CODE=event}."""
    ids, codes = extract(text)
    names = ["BASE" if i == "DISPATCH" else code_name(i, base) for i in ids]
    prefix = f"[{', '.join(names)}] " if names else ""
    codetag = " {" + ", ".join(f"{c}={l}" if l else c for c, l in codes) + "}" if codes else ""
    return f"[{ts_str}] {prefix}{text}{codetag}"


def line_ids(text: str, base: str | Path) -> list[str]:
    """The code names of units/operators heard in a line (for correlation)."""
    ids, _ = extract(text)
    return ["BASE" if i == "DISPATCH" else code_name(i, base) for i in ids]
