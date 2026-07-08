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


_SERVICE_KW = {
    "EMS": r"\b(medical|ambulance|medic|patient|gsw|unconscious|breathing|cardiac|"
           r"overdose|\bod\b|injury|bleeding|cpr|als|bls|902|1141|fall victim|seizure)\b",
    "Fire": r"\b(fire|engine|structure|smoke|flames|brush|hydrant|ladder|battalion|"
            r"fully involved|working fire|grass fire|vegetation)\b",
    "CHP": r"\b(chp|highway|freeway|interstate|i-?80|i-?680|i-?505|sr-?\d+|sig-?alert|"
           r"traffic break|1179|1180|1181|1125|20001|20002|23152|off ?ramp|on ?ramp)\b",
    "Police": r"\b(officer|suspect|deputy|warrant|in custody|211|459|415|5150|242|240|"
              r"245|207|187|10851|417|foot pursuit|code ?3|pd\b)\b",
}


def classify_service(text: str) -> str:
    """Which service this radio traffic belongs to (EMS/Fire/CHP/Police), so an
    event's transcript groups by who is talking. Highest keyword hit-count wins."""
    low = text.lower()
    best, score = "Dispatch", 0
    for svc, pat in _SERVICE_KW.items():
        n = len(re.findall(pat, low, re.I))
        if n > score:
            best, score = svc, n
    return best


_STATUS = [
    (r"shots?\s*fired|gunshot|11-?99", "shots fired / officer in danger"),
    (r"structure\s*fire|fully involved|working fire", "working structure fire"),
    (r"\bfire\s*(is\s*)?(out|contained|knocked)", "fire contained"),
    (r"on\s*scene|10-?97", "units on scene"),
    (r"en\s*route|responding|10-?76", "units en route"),
    (r"code\s*3", "running code 3 (lights + siren)"),
    (r"in\s*custody|10-?15", "suspect in custody"),
    (r"pursuit|fleeing|foot\s*chase", "active pursuit"),
    (r"code\s*4|10-?98|clear the?\s*(air|call)", "situation under control"),
    (r"transport(ing)?|to the hospital|code\s*3\s*transport", "patient being transported"),
    (r"\bgsw\b|gunshot wound|shot victim", "gunshot victim"),
    (r"unconscious|not breathing|cardiac|cpr", "medical emergency, patient down"),
]


def summarize(segments: list[dict], service: str = "Dispatch", call: str | None = None) -> str:
    """Plain-English summary of a radio conversation: decodes the jargon (codes ->
    events, status phrases) so the operator understands it at a glance. No LLM."""
    if not segments:
        return ""
    text = " ".join(s.get("text", "") for s in segments).lower()
    events: list[str] = []
    speakers: set[str] = set()
    for s in segments:
        if s.get("speaker"):
            speakers.add(s["speaker"])
        for c in s.get("codes", []):
            lbl = c.split("=", 1)[1].strip() if "=" in c else ""
            if lbl:
                events.append(lbl)
    events = list(dict.fromkeys(events))
    officers = sorted(sp for sp in speakers if sp and sp != "Dispatcher")
    statuses = list(dict.fromkeys(phrase for pat, phrase in _STATUS if re.search(pat, text)))
    loc = f" at {call}" if call else ""
    lead = f"{service} call{loc}"
    if events:
        lead += ": " + ", ".join(events)
    bits = [lead + "."]
    if statuses:
        s0 = ", ".join(statuses)
        bits.append(s0[0].upper() + s0[1:] + ".")
    if officers:
        bits.append(f"{len(officers)} unit{'s' if len(officers) != 1 else ''} involved ({', '.join(officers)}).")
    return " ".join(bits)


def speaker_segments(text: str) -> list[dict]:
    """Attribute each transcript line to a speaker so the operator reads WHO said
    WHAT: dispatch chatter -> 'Dispatcher'; each distinct unit -> 'Officer 1/2/...'
    (numbered per transcript in order of appearance). Heuristic, no diarization."""
    out: list[dict] = []
    officer_map: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        ts = ""
        m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)  # pull a leading [time]
        if m:
            ts, line = m.group(1), m.group(2)
        line = re.sub(r"^\[[^\]]*\]\s*", "", line)     # drop any [CODENAMES] prefix
        line = re.sub(r"\s*\{[^}]*\}\s*$", "", line)    # drop a trailing {CODE=event}
        if not line:
            continue
        ids, codes = extract(line)
        non_dispatch = [i for i in ids if i != "DISPATCH"]
        if "DISPATCH" in ids or not non_dispatch:
            speaker = "Dispatcher"
        else:
            unit = non_dispatch[0]
            officer_map.setdefault(unit, f"Officer {len(officer_map) + 1}")
            speaker = officer_map[unit]
        out.append({
            "speaker": speaker,
            "time": ts,
            "text": line,
            "codes": [f"{c}={l}" if l else c for c, l in codes],
        })
    return out
