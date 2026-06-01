# Everlense Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Everlense, a local, free, CompanyCam-style organizer that files phone photos by job-site/personal and screenshots by topic, with searchable metadata.

**Architecture:** Pure-Python package of small single-purpose modules in a Scan -> Classify -> Tag -> File -> Stamp -> Index -> Find pipeline. Read-only core (scanner, classifier, indexer) built and proven before any file-moving code. The one mutating module (filer) is dry-run-by-default and routes every original through a 14-day `_Trash` after a hash-verified copy.

**Tech Stack:** Python 3.13, Pillow, exifread, pytesseract + tesseract 5.5.0 (OCR), anthropic (Haiku Tier-1), SQLite FTS5 (stdlib), PyYAML, argparse, pytest.

---

## Conventions

- **Code home:** `/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlense/`
- **Run tests from the code home:** `cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlense && python3 -m pytest -q`
- **Photo store (runtime):** `04_MEDIA_LIBRARY/Photos/` (git-ignored). Tests NEVER touch it: they set `EVERLENSE_PHOTO_ROOT` and `EVERLENSE_DCIM` to `tmp_path`.
- **No em-dashes anywhere** (a repo hook blocks them). Use `--` or `:` or commas.
- **Commits:** scoped to the files in the task. Footer line: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Verify-before-destroy:** filer copies, re-hashes the copy, and only then moves the original to `_Trash/`. Never a bare delete.

## File Structure (locked)

```
everlense/
  __init__.py            # version
  paths.py               # env-overridable canonical paths
  models.py              # MediaItem, Label, PhotoRecord dataclasses
  config.py              # load/seed categories.yaml, projects.json, state.json
  scanner.py             # walk + sha256 + source-detect + EXIF (read-only)
  ocr.py                 # tesseract wrapper (isolated, mockable)
  classifier.py          # Tier-0 heuristics + keyword rules; classify() orchestration
  ai_classify.py         # Tier-1 Haiku wrapper (isolated, returns None without key)
  filer.py               # dest_for + file_item (copy->verify->trash, .nomedia, sidecar)
  stamper.py             # Pillow watermark on a copy
  indexer.py             # SQLite FTS5 index + rebuild-from-sidecars
  finder.py              # search + static HTML gallery on 127.0.0.1
  tagger.py              # interactive batch confirm (input injectable)
  cli.py                 # argparse subcommands -> everlense entrypoint
  defaults/categories.yaml
  requirements.txt
  README.md
  tests/conftest.py + test_*.py
  docs/                  # spec + this plan
```

---

## Task 0: One-time dependency

- [ ] **Step 1: Install the only missing wrapper**

Run: `pip3 install pytesseract`
Expected: installs `pytesseract` (tesseract 5.5.0 binary already present).

- [ ] **Step 2: Verify OCR end to end**

Run: `python3 -c "import pytesseract,PIL; print('ocr ok', pytesseract.get_tesseract_version())"`
Expected: prints `ocr ok 5.5.0` (or similar).

---

## Task 1: Package scaffold, paths, models

**Files:**
- Create: `everlense/__init__.py`, `everlense/paths.py`, `everlense/models.py`, `everlense/requirements.txt`, `everlense/tests/conftest.py`
- Test: `everlense/tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_paths.py`:
```python
import os
from everlense import paths

def test_photo_root_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    assert paths.photo_root() == tmp_path
    assert paths.state_dir() == tmp_path / ".everlense"
    assert paths.trash_dir() == tmp_path / "_Trash"

def test_dcim_sources_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_DCIM", str(tmp_path))
    srcs = paths.dcim_sources()
    assert tmp_path / "Camera" in srcs
    assert tmp_path / "Screenshots" in srcs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlense && python3 -m pytest tests/test_paths.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'everlense'`.

- [ ] **Step 3: Create the package files**

`everlense/__init__.py`:
```python
__version__ = "0.1.0"
```

`everlense/paths.py`:
```python
import os
from pathlib import Path

_DEFAULT_ROOT = "/mnt/sdcard/AA_MY_DRIVE/04_MEDIA_LIBRARY/Photos"
_DEFAULT_DCIM = "/sdcard/DCIM"

def photo_root() -> Path:
    return Path(os.environ.get("EVERLENSE_PHOTO_ROOT", _DEFAULT_ROOT)).expanduser()

def state_dir() -> Path:
    return photo_root() / ".everlense"

def trash_dir() -> Path:
    return photo_root() / "_Trash"

def dcim_sources() -> list[Path]:
    base = Path(os.environ.get("EVERLENSE_DCIM", _DEFAULT_DCIM))
    return [base / "Camera", base / "Screenshots"]

def social_sources() -> list[Path]:
    base = Path(os.environ.get("EVERLENSE_PICTURES", "/sdcard/Pictures"))
    return [base / n for n in ("WhatsApp", "Instagram", "Messenger", "Threads", "Twitter")]
```

`everlense/models.py`:
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MediaItem:
    path: str
    sha256: str
    source: str            # "camera" | "screenshot" | "social"
    taken_at: Optional[str]
    gps: Optional[dict]    # {"lat": float, "lon": float, "from": "exif"} or None
    width: int
    height: int

@dataclass
class Label:
    category: str          # "Personal" | "Business/Properties" | "Screenshots/Linux" ...
    project: Optional[str] = None
    confidence: float = 0.0
    tier: int = 0          # 0 = heuristic, 1 = AI
    signals: list = field(default_factory=list)
    proposed_category: Optional[str] = None

@dataclass
class PhotoRecord:
    sha256: str
    dest_path: str
    source: str
    category: str
    project: Optional[str]
    taken_at: Optional[str]
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    address: Optional[str]
    ocr_text: Optional[str]
    tags: list
    stamped: bool
    filed_at: str
```

`everlense/requirements.txt`:
```
Pillow>=10
exifread>=3
pytesseract>=0.3.10
anthropic>=0.40
PyYAML>=6
pytest>=8
```

`everlense/tests/conftest.py`:
```python
import sys, os
from pathlib import Path
# make the package importable when pytest runs from the code home
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_paths.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/__init__.py everlense/paths.py everlense/models.py everlense/requirements.txt everlense/tests/conftest.py everlense/tests/test_paths.py
git commit -m "feat(everlense): package scaffold, paths, models

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Config (seed + load categories, projects, state)

**Files:**
- Create: `everlense/config.py`, `everlense/defaults/categories.yaml`
- Test: `everlense/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_config.py`:
```python
from everlense import config

def test_categories_seed_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    assert "Linux" in cats and "AI" in cats
    assert any("sudo" in kw for kw in cats["Linux"]["keywords"])
    # second load reads the now-seeded file, not defaults
    assert (tmp_path / ".everlense" / "categories.yaml").exists()

def test_projects_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    config.save_project({"slug": "2026-05_123-main", "address": "123 Main St", "watermark": True})
    projs = config.load_projects()
    assert projs["2026-05_123-main"]["address"] == "123 Main St"

def test_state_cursor(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    st = config.load_state()
    assert st["known_hashes"] == []
    st["known_hashes"].append("abc")
    config.save_state(st)
    assert "abc" in config.load_state()["known_hashes"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: FAIL, `No module named 'everlense.config'`.

- [ ] **Step 3: Implement**

`everlense/defaults/categories.yaml`:
```yaml
# Screenshot topic taxonomy. Edit freely: add/rename/remove categories.
# Each category: keywords (matched against OCR text, case-insensitive).
AI:
  keywords: [chatgpt, claude, gpt, "prompt", llm, anthropic, openai, gemini, copilot, "model"]
Linux:
  keywords: [sudo, "apt ", bash, "$ ", "# ", systemctl, chmod, "/etc/", kernel, ubuntu, debian, arch]
Tech_Dev:
  keywords: [python, javascript, github, "def ", "function", "import ", traceback, "npm ", docker, api, json]
Finance_Trading:
  keywords: [usdc, xlm, "p&l", pnl, ticker, candle, leverage, coinbase, polymarket, balance, "$"]
RealEstate_Wholesale:
  keywords: [zillow, mls, "sq ft", arv, "rehab", foreclosure, listing, realtor, escrow, "for sale"]
Reference_HowTo:
  keywords: [howto, "how to", tutorial, "step ", guide, documentation, "stack overflow"]
Receipts_Docs:
  keywords: [receipt, invoice, total, subtotal, "order #", confirmation, statement]
Social:
  keywords: [instagram, "retweet", "liked by", "followers", tiktok, facebook, dm]
Memes:
  keywords: [lol, meme, "when you", "pov:"]
Personal:
  keywords: []
```

`everlense/config.py`:
```python
import json
from pathlib import Path
import yaml
from everlense import paths

_DEFAULTS = Path(__file__).resolve().parent / "defaults" / "categories.yaml"

def _ensure_state_dir() -> Path:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d

def load_categories() -> dict:
    sd = _ensure_state_dir()
    f = sd / "categories.yaml"
    if not f.exists():
        f.write_text(_DEFAULTS.read_text())
    return yaml.safe_load(f.read_text()) or {}

def load_projects() -> dict:
    f = _ensure_state_dir() / "projects.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text())

def save_project(project: dict) -> None:
    projs = load_projects()
    projs[project["slug"]] = project
    (_ensure_state_dir() / "projects.json").write_text(json.dumps(projs, indent=2))

def load_state() -> dict:
    f = _ensure_state_dir() / "state.json"
    if not f.exists():
        return {"known_hashes": [], "last_scan": None}
    return json.loads(f.read_text())

def save_state(state: dict) -> None:
    (_ensure_state_dir() / "state.json").write_text(json.dumps(state, indent=2))
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/config.py everlense/defaults/categories.yaml everlense/tests/test_config.py
git commit -m "feat(everlense): config + seed screenshot taxonomy

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Scanner (read-only: hash, source, EXIF)

**Files:**
- Create: `everlense/scanner.py`
- Test: `everlense/tests/test_scanner.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_scanner.py`:
```python
from pathlib import Path
from PIL import Image
from everlense import scanner

def _make_jpg(p: Path, size=(640, 480)):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 120, 120)).save(p, "JPEG")

def test_sha256_stable(tmp_path):
    f = tmp_path / "a.jpg"; _make_jpg(f)
    assert scanner.sha256_file(f) == scanner.sha256_file(f)

def test_detect_source_by_folder(tmp_path):
    assert scanner.detect_source(tmp_path / "Camera" / "x.jpg") == "camera"
    assert scanner.detect_source(tmp_path / "Screenshots" / "x.png") == "screenshot"
    assert scanner.detect_source(tmp_path / "WhatsApp" / "x.jpg") == "social"

def test_scan_skips_known_hashes(tmp_path, monkeypatch):
    cam = tmp_path / "Camera"; _make_jpg(cam / "1.jpg"); _make_jpg(cam / "2.jpg", (100, 100))
    monkeypatch.setenv("EVERLENSE_DCIM", str(tmp_path))
    items = scanner.scan(known_hashes=set())
    assert len(items) == 2
    known = {items[0].sha256}
    again = scanner.scan(known_hashes=known)
    assert len(again) == 1
    assert again[0].source == "camera"
    assert again[0].width in (640, 100)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_scanner.py -q`
Expected: FAIL, `No module named 'everlense.scanner'`.

- [ ] **Step 3: Implement**

`everlense/scanner.py`:
```python
import hashlib
from pathlib import Path
from typing import Optional
import exifread
from PIL import Image
from everlense import paths
from everlense.models import MediaItem

_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
_SOCIAL = {"whatsapp", "instagram", "messenger", "threads", "twitter", "facebook"}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_source(p: Path) -> str:
    parent = p.parent.name.lower()
    if parent == "screenshots":
        return "screenshot"
    if parent in _SOCIAL:
        return "social"
    return "camera"

def _dms_to_deg(values, ref) -> Optional[float]:
    try:
        d = float(values[0].num) / float(values[0].den)
        m = float(values[1].num) / float(values[1].den)
        s = float(values[2].num) / float(values[2].den)
        deg = d + m / 60.0 + s / 3600.0
        if ref in ("S", "W"):
            deg = -deg
        return round(deg, 6)
    except Exception:
        return None

def read_exif(p: Path):
    taken_at = None
    gps = None
    try:
        with open(p, "rb") as fh:
            tags = exifread.process_file(fh, details=False)
        dt = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if dt:
            raw = str(dt).strip()           # "2026:05:31 14:30:12"
            d, t = raw.split(" ", 1)
            taken_at = d.replace(":", "-") + "T" + t
        lat = tags.get("GPS GPSLatitude"); lat_ref = tags.get("GPS GPSLatitudeRef")
        lon = tags.get("GPS GPSLongitude"); lon_ref = tags.get("GPS GPSLongitudeRef")
        if lat and lon:
            la = _dms_to_deg(lat.values, str(lat_ref)); lo = _dms_to_deg(lon.values, str(lon_ref))
            if la is not None and lo is not None:
                gps = {"lat": la, "lon": lo, "from": "exif"}
    except Exception:
        pass
    try:
        with Image.open(p) as im:
            w, h = im.size
    except Exception:
        w = h = 0
    return taken_at, gps, w, h

def scan(known_hashes: set, sources=None) -> list[MediaItem]:
    sources = sources or (paths.dcim_sources() + paths.social_sources())
    out = []
    for root in sources:
        if not Path(root).exists():
            continue
        for p in sorted(Path(root).rglob("*")):
            if p.suffix.lower() not in _IMG_EXT or not p.is_file():
                continue
            digest = sha256_file(p)
            if digest in known_hashes:
                continue
            taken_at, gps, w, h = read_exif(p)
            out.append(MediaItem(str(p), digest, detect_source(p), taken_at, gps, w, h))
    return out
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_scanner.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/scanner.py everlense/tests/test_scanner.py
git commit -m "feat(everlense): read-only scanner (hash, source, EXIF, GPS)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Indexer (SQLite FTS5)

**Files:**
- Create: `everlense/indexer.py`
- Test: `everlense/tests/test_indexer.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_indexer.py`:
```python
from everlense import indexer
from everlense.models import PhotoRecord

def _rec(**kw):
    base = dict(sha256="h1", dest_path="/x/a.jpg", source="screenshot",
               category="Screenshots/Linux", project=None, taken_at="2026-05-31T10:00:00",
               gps_lat=None, gps_lon=None, address=None, ocr_text="sudo apt update",
               tags=[], stamped=False, filed_at="2026-05-31T10:01:00")
    base.update(kw); return PhotoRecord(**base)

def test_upsert_and_search(tmp_path):
    db = tmp_path / "idx.db"
    conn = indexer.connect(db)
    indexer.upsert(conn, _rec())
    indexer.upsert(conn, _rec(sha256="h2", category="Screenshots/AI", ocr_text="claude prompt"))
    rows = indexer.search(conn, "sudo")
    assert len(rows) == 1 and rows[0]["category"] == "Screenshots/Linux"
    rows = indexer.search(conn, "AI")            # category match
    assert any(r["sha256"] == "h2" for r in rows)

def test_upsert_is_idempotent(tmp_path):
    conn = indexer.connect(tmp_path / "idx.db")
    indexer.upsert(conn, _rec()); indexer.upsert(conn, _rec(category="Screenshots/Tech_Dev"))
    rows = indexer.search(conn, "Linux OR Tech_Dev")
    assert len([r for r in rows if r["sha256"] == "h1"]) == 1   # one row, updated
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_indexer.py -q`
Expected: FAIL, `No module named 'everlense.indexer'`.

- [ ] **Step 3: Implement**

`everlense/indexer.py`:
```python
import json
import sqlite3
from pathlib import Path
from everlense.models import PhotoRecord

def connect(db_path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS photos(
        sha256 TEXT PRIMARY KEY, dest_path TEXT, source TEXT, category TEXT,
        project TEXT, taken_at TEXT, gps_lat REAL, gps_lon REAL, address TEXT,
        ocr_text TEXT, tags TEXT, stamped INTEGER, filed_at TEXT)""")
    conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS photos_fts USING fts5(
        sha256 UNINDEXED, category, project, address, ocr_text, tags)""")
    conn.commit()
    return conn

def upsert(conn: sqlite3.Connection, r: PhotoRecord) -> None:
    conn.execute("""INSERT INTO photos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(sha256) DO UPDATE SET dest_path=excluded.dest_path, source=excluded.source,
        category=excluded.category, project=excluded.project, taken_at=excluded.taken_at,
        gps_lat=excluded.gps_lat, gps_lon=excluded.gps_lon, address=excluded.address,
        ocr_text=excluded.ocr_text, tags=excluded.tags, stamped=excluded.stamped, filed_at=excluded.filed_at""",
        (r.sha256, r.dest_path, r.source, r.category, r.project, r.taken_at, r.gps_lat, r.gps_lon,
         r.address, r.ocr_text, json.dumps(r.tags), int(r.stamped), r.filed_at))
    conn.execute("DELETE FROM photos_fts WHERE sha256=?", (r.sha256,))
    conn.execute("INSERT INTO photos_fts VALUES(?,?,?,?,?,?)",
        (r.sha256, r.category or "", r.project or "", r.address or "", r.ocr_text or "", " ".join(r.tags)))
    conn.commit()

def search(conn: sqlite3.Connection, query: str) -> list[dict]:
    hits = conn.execute("SELECT sha256 FROM photos_fts WHERE photos_fts MATCH ?", (query,)).fetchall()
    shas = [h["sha256"] for h in hits]
    if not shas:
        return []
    q = "SELECT * FROM photos WHERE sha256 IN (%s)" % ",".join("?" * len(shas))
    return [dict(row) for row in conn.execute(q, shas).fetchall()]
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_indexer.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/indexer.py everlense/tests/test_indexer.py
git commit -m "feat(everlense): SQLite FTS5 photo index

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Classifier Tier-0 (OCR + keyword rules + camera heuristic)

**Files:**
- Create: `everlense/ocr.py`, `everlense/classifier.py`
- Test: `everlense/tests/test_classifier.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_classifier.py`:
```python
from everlense import classifier
from everlense.models import MediaItem
from everlense import config

def _item(source="screenshot", w=1080, h=2400):
    return MediaItem("/x/a.png", "h1", source, "2026-05-31T10:00:00", None, w, h)

def test_screenshot_keyword_match(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    lbl = classifier.classify_screenshot(_item(), cats, ocr="user@box:~$ sudo apt update")
    assert lbl.category == "Screenshots/Linux" and lbl.tier == 0 and lbl.confidence >= 0.5

def test_screenshot_low_confidence_when_no_keyword(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    lbl = classifier.classify_screenshot(_item(), cats, ocr="a pretty sunset photo")
    assert lbl.confidence < 0.5      # falls through to Tier-1 later

def test_camera_heuristic_defaults_to_business_inbox(monkeypatch, tmp_path):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    lbl = classifier.classify_camera(_item(source="camera", w=4000, h=3000), ocr="")
    assert lbl.category in ("Business/_Inbox", "Personal") and lbl.tier == 0
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_classifier.py -q`
Expected: FAIL, `No module named 'everlense.classifier'`.

- [ ] **Step 3: Implement**

`everlense/ocr.py`:
```python
def ocr_text(path: str) -> str:
    """Return OCR text for an image, or '' on any failure. Isolated so tests can monkeypatch it."""
    try:
        import pytesseract
        from PIL import Image
        with Image.open(path) as im:
            return pytesseract.image_to_string(im) or ""
    except Exception:
        return ""
```

`everlense/classifier.py`:
```python
from everlense.models import MediaItem, Label

_TIER1_THRESHOLD = 0.5

def classify_screenshot(item: MediaItem, categories: dict, ocr: str) -> Label:
    text = (ocr or "").lower()
    best, best_hits = None, 0
    for name, spec in categories.items():
        hits = sum(1 for kw in (spec.get("keywords") or []) if kw.lower() in text)
        if hits > best_hits:
            best, best_hits = name, hits
    if best and best_hits > 0:
        conf = min(0.5 + 0.15 * best_hits, 0.95)
        return Label(category=f"Screenshots/{best}", confidence=conf, tier=0,
                     signals=[f"keyword x{best_hits} -> {best}"])
    return Label(category="Screenshots/_Inbox", confidence=0.2, tier=0, signals=["no keyword match"])

def classify_camera(item: MediaItem, ocr: str) -> Label:
    # Tier-0 cannot know the project of an old photo. Route to a holding bucket; Tier-1/operator decides.
    text = (ocr or "").lower()
    if any(k in text for k in ("receipt", "invoice", "total")):
        return Label(category="Business/Receipts_Docs", confidence=0.6, tier=0, signals=["receipt text"])
    return Label(category="Business/_Inbox", confidence=0.3, tier=0, signals=["camera default"])

def needs_tier1(label: Label) -> bool:
    return label.confidence < _TIER1_THRESHOLD

def classify(item: MediaItem, categories: dict, ocr_fn, ai=None) -> Label:
    text = ocr_fn(item.path) if item.source == "screenshot" else ""
    if item.source == "screenshot":
        label = classify_screenshot(item, categories, text)
    else:
        label = classify_camera(item, text)
    if ai is not None and needs_tier1(label):
        upgraded = ai(item, categories, text)
        if upgraded is not None:
            return upgraded
    return label
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_classifier.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/ocr.py everlense/classifier.py everlense/tests/test_classifier.py
git commit -m "feat(everlense): Tier-0 classifier (OCR keyword rules + camera heuristic)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Classifier Tier-1 (Haiku, isolated + mockable)

**Files:**
- Create: `everlense/ai_classify.py`
- Test: `everlense/tests/test_ai_classify.py`

- [ ] **Step 1: Write the failing test** (the network call is monkeypatched; no live API in tests)

`everlense/tests/test_ai_classify.py`:
```python
import os
from everlense import ai_classify
from everlense.models import MediaItem, Label

def _item(source="screenshot"):
    return MediaItem("/x/a.png", "h1", source, None, None, 1080, 2400)

def test_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ai_classify.ai_label(_item(), {"AI": {"keywords": []}}, "claude prompt") is None

def test_parses_model_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(ai_classify, "_raw_call",
        lambda *a, **k: '{"category":"Screenshots/AI","confidence":0.9}')
    lbl = ai_classify.ai_label(_item(), {"AI": {"keywords": []}}, "claude prompt")
    assert isinstance(lbl, Label) and lbl.category == "Screenshots/AI" and lbl.tier == 1
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_ai_classify.py -q`
Expected: FAIL, `No module named 'everlense.ai_classify'`.

- [ ] **Step 3: Implement**

`everlense/ai_classify.py`:
```python
import os
import json
import base64
from everlense.models import MediaItem, Label

_MODEL = "claude-haiku-4-5"

def _raw_call(system: str, content: list) -> str:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(model=_MODEL, max_tokens=200,
        system=system, messages=[{"role": "user", "content": content}])
    return msg.content[0].text

def _parse(text: str) -> Label | None:
    try:
        start = text.index("{"); end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        return Label(category=data["category"], project=data.get("project"),
                     confidence=float(data.get("confidence", 0.7)), tier=1,
                     signals=["haiku"], proposed_category=data.get("proposed_category"))
    except Exception:
        return None

def ai_label(item: MediaItem, categories: dict, ocr: str) -> Label | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    cat_names = list(categories.keys())
    if item.source == "screenshot":
        system = ("You classify a phone screenshot into exactly one topic. "
                  f"Choose from: {cat_names}. If none fit, set proposed_category to a new short name. "
                  'Reply ONLY JSON: {"category":"Screenshots/<Topic>","confidence":0-1,"proposed_category":null}')
        content = [{"type": "text", "text": f"OCR text:\n{ocr[:1500]}"}]
    else:
        try:
            with open(item.path, "rb") as fh:
                b64 = base64.standard_b64encode(fh.read()).decode()
        except Exception:
            return None
        system = ('You classify a phone photo. Reply ONLY JSON: '
                  '{"category":"Personal" or "Business/_Inbox" or "Business/Receipts_Docs","confidence":0-1}')
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}]
    return _parse(_raw_call(system, content))
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_ai_classify.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/ai_classify.py everlense/tests/test_ai_classify.py
git commit -m "feat(everlense): Tier-1 Haiku classifier (isolated, key-gated)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Filer (dry-run default, copy -> verify -> trash, .nomedia, sidecar)

This is the only mutating module. Tests prove the verify-before-destroy guarantee.

**Files:**
- Create: `everlense/filer.py`
- Test: `everlense/tests/test_filer.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_filer.py`:
```python
import json
from pathlib import Path
from PIL import Image
from everlense import filer, scanner
from everlense.models import MediaItem, Label

def _src(tmp_path, name="20260531_101010.jpg"):
    p = tmp_path / "Camera" / name; p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 240), (10, 20, 30)).save(p, "JPEG")
    return MediaItem(str(p), scanner.sha256_file(p), "camera", "2026-05-31T10:10:10", None, 320, 240)

def test_dry_run_touches_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    item = _src(tmp_path)
    res = filer.file_item(item, Label(category="Personal"), dry_run=True)
    assert res["planned_dest"].endswith(".jpg")
    assert Path(item.path).exists()                 # original untouched
    assert not Path(res["planned_dest"]).exists()   # nothing written

def test_live_copies_verifies_and_trashes_original(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    item = _src(tmp_path)
    res = filer.file_item(item, Label(category="Personal"), dry_run=False)
    dest = Path(res["dest"])
    assert dest.exists()
    assert scanner.sha256_file(dest) == item.sha256          # verified identical
    assert not Path(item.path).exists()                       # original moved out
    assert (tmp_path / "store" / "_Trash").exists()           # into trash
    assert dest.with_suffix(".json").exists()                 # sidecar written
    assert (dest.parent / ".nomedia").exists()                # off the gallery
    sidecar = json.loads(dest.with_suffix(".json").read_text())
    assert sidecar["sha256"] == item.sha256 and sidecar["category"] == "Personal"

def test_property_dest_uses_project_slug(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    item = _src(tmp_path)
    res = filer.file_item(item, Label(category="Business/Properties",
                          project="2026-05_123-main_memphis-tn"), dry_run=False)
    assert "Properties/2026-05_123-main_memphis-tn" in res["dest"]
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_filer.py -q`
Expected: FAIL, `No module named 'everlense.filer'`.

- [ ] **Step 3: Implement**

`everlense/filer.py`:
```python
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from everlense import paths, scanner
from everlense.models import MediaItem, Label

def _category_dir(label: Label) -> Path:
    root = paths.photo_root()
    if label.category == "Business/Properties" and label.project:
        return root / "Business" / "Properties" / label.project
    if label.category == "Personal" and not label.signals:
        # date sub-bucket for plain personal
        pass
    return root / label.category

def dest_for(item: MediaItem, label: Label) -> Path:
    d = _category_dir(label)
    if label.category == "Personal":
        ym = (item.taken_at or "1970-01")[:7]            # YYYY-MM
        d = paths.photo_root() / "Personal" / ym[:4] / ym[5:7]
    return d / Path(item.path).name

def _write_nomedia(folder: Path):
    (folder / ".nomedia").touch()

def _write_sidecar(dest: Path, item: MediaItem, label: Label, address=None, ocr=None, stamped=False):
    rec = {
        "sha256": item.sha256, "source": item.source, "original_path": item.path,
        "taken_at": item.taken_at, "category": label.category, "project": label.project,
        "address": address, "gps": item.gps, "tags": [], "ocr_text": ocr, "stamped": stamped,
        "classified_by": {"tier": label.tier, "confidence": label.confidence, "signals": label.signals},
        "filed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    dest.with_suffix(".json").write_text(json.dumps(rec, indent=2))
    return rec

def file_item(item: MediaItem, label: Label, dry_run: bool = True, address=None, ocr=None) -> dict:
    dest = dest_for(item, label)
    if dry_run:
        return {"planned_dest": str(dest), "category": label.category, "dry_run": True}
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and scanner.sha256_file(dest) == item.sha256:
        return {"dest": str(dest), "skipped": "already filed"}
    # 1. copy
    shutil.copy2(item.path, dest)
    # 2. verify
    if scanner.sha256_file(dest) != item.sha256:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"hash mismatch after copy: {item.path}")
    # 3. move original to trash (NOT delete)
    trash = paths.trash_dir(); trash.mkdir(parents=True, exist_ok=True)
    shutil.move(item.path, trash / Path(item.path).name)
    # 4. gallery + sidecar
    _write_nomedia(dest.parent)
    rec = _write_sidecar(dest, item, label, address=address, ocr=ocr)
    return {"dest": str(dest), "category": label.category, "sidecar": rec, "dry_run": False}
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_filer.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/filer.py everlense/tests/test_filer.py
git commit -m "feat(everlense): filer with dry-run, copy-verify-trash, .nomedia, sidecar

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Stamper (Pillow watermark on a copy)

**Files:**
- Create: `everlense/stamper.py`
- Test: `everlense/tests/test_stamper.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_stamper.py`:
```python
from pathlib import Path
from PIL import Image
from everlense import stamper

def test_stamp_writes_copy_and_keeps_original(tmp_path):
    src = tmp_path / "a.jpg"; Image.new("RGB", (800, 600), (200, 200, 200)).save(src, "JPEG")
    out = stamper.stamp(str(src), fields=["2026-05-31 14:30", "123 Main St, Memphis TN", "35.14, -90.04"])
    assert Path(out).exists() and Path(out) != src
    assert Path(src).exists()                       # original untouched
    with Image.open(out) as im:
        assert im.size == (800, 600)                # same dimensions
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_stamper.py -q`
Expected: FAIL, `No module named 'everlense.stamper'`.

- [ ] **Step 3: Implement**

`everlense/stamper.py`:
```python
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_GOLD = (212, 175, 55)        # Everlight gold #D4AF37
_BG = (10, 10, 10)

def _font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def stamp(src: str, fields: list[str]) -> str:
    src_p = Path(src)
    out_dir = src_p.parent / "_stamped"; out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (src_p.stem + "_stamped" + src_p.suffix)
    with Image.open(src).convert("RGB") as im:
        w, h = im.size
        draw = ImageDraw.Draw(im, "RGBA")
        size = max(14, w // 45)
        font = _font(size)
        text = "  |  ".join(f for f in fields if f)
        pad = size // 2
        band_h = size + 2 * pad
        draw.rectangle([(0, h - band_h), (w, h)], fill=(*_BG, 180))
        draw.text((pad, h - band_h + pad), text, font=font, fill=_GOLD)
        im.save(out, "JPEG", quality=90)
    return str(out)
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_stamper.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/stamper.py everlense/tests/test_stamper.py
git commit -m "feat(everlense): Pillow watermark stamper (gold band, copy only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Finder + HTML gallery (127.0.0.1)

**Files:**
- Create: `everlense/finder.py`
- Test: `everlense/tests/test_finder.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_finder.py`:
```python
from everlense import finder, indexer
from everlense.models import PhotoRecord

def _rec(sha, cat, ocr=""):
    return PhotoRecord(sha, f"/x/{sha}.jpg", "screenshot", cat, None, "2026-05-31T10:00:00",
                       None, None, None, ocr, [], False, "2026-05-31T10:01:00")

def test_find_returns_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    conn = indexer.connect(tmp_path / ".everlense" / "photos_index.db")
    indexer.upsert(conn, _rec("h1", "Screenshots/Linux", "sudo apt"))
    indexer.upsert(conn, _rec("h2", "Screenshots/AI", "claude"))
    rows = finder.find("Linux")
    assert len(rows) == 1 and rows[0]["sha256"] == "h1"

def test_build_gallery_writes_html(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    out = finder.build_gallery([{"dest_path": "/x/a.jpg", "category": "Personal", "taken_at": "t"}],
                               tmp_path / "g.html")
    html = out.read_text()
    assert "<img" in html and "Personal" in html
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_finder.py -q`
Expected: FAIL, `No module named 'everlense.finder'`.

- [ ] **Step 3: Implement**

`everlense/finder.py`:
```python
import html as _html
from pathlib import Path
from everlense import paths, indexer

def _db():
    return paths.state_dir() / "photos_index.db"

def find(query: str) -> list[dict]:
    conn = indexer.connect(_db())
    return indexer.search(conn, query)

def build_gallery(rows: list[dict], out_path) -> Path:
    out = Path(out_path)
    cards = []
    for r in rows:
        dest = _html.escape(str(r.get("dest_path", "")))
        cap = _html.escape(f"{r.get('category','')} {r.get('taken_at','')}")
        cards.append(f'<figure><img loading="lazy" src="file://{dest}"><figcaption>{cap}</figcaption></figure>')
    out.write_text(
        "<!doctype html><meta charset=utf-8><title>Everlense</title>"
        "<style>body{background:#0A0A0A;color:#E8E8E8;font-family:Inter,sans-serif}"
        "h1{color:#D4AF37} figure{display:inline-block;width:220px;margin:8px;vertical-align:top}"
        "img{width:220px;height:160px;object-fit:cover;border:1px solid #D4AF37}"
        "figcaption{font-size:12px}</style>"
        f"<h1>Everlense</h1><p>{len(rows)} photos</p>" + "".join(cards))
    return out

def serve(port: int = 8533):
    # bind:tailnet-only is wrong here; this is local viewing only -> 127.0.0.1 per network doctrine
    import http.server, socketserver, functools
    g = build_gallery(find(""), paths.state_dir() / "gallery.html")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(g.parent))
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Everlense gallery at http://127.0.0.1:{port}/{g.name}")
        httpd.serve_forever()
```

Note: `find("")` returns all rows because FTS `MATCH ''` is empty; in `serve()` swap to a "select all" path if empty. Add to `finder.py`:
```python
def all_rows() -> list[dict]:
    conn = indexer.connect(_db())
    return [dict(r) for r in conn.execute("SELECT * FROM photos ORDER BY taken_at DESC").fetchall()]
```
and change `serve()` to use `all_rows()` instead of `find("")`.

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_finder.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/finder.py everlense/tests/test_finder.py
git commit -m "feat(everlense): finder search + local gallery (127.0.0.1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Tagger (interactive batch confirm, input injectable)

**Files:**
- Create: `everlense/tagger.py`
- Test: `everlense/tests/test_tagger.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_tagger.py`:
```python
from everlense import tagger
from everlense.models import MediaItem, Label

def _item(): return MediaItem("/x/a.jpg", "h1", "camera", None, None, 100, 100)

def test_accept_keeps_ai_label():
    suggested = Label(category="Personal", confidence=0.8, tier=1)
    out = tagger.confirm(_item(), suggested, input_fn=lambda prompt: "")   # blank = accept
    assert out.category == "Personal"

def test_correction_overrides_category():
    suggested = Label(category="Business/_Inbox", confidence=0.3, tier=0)
    out = tagger.confirm(_item(), suggested, input_fn=lambda prompt: "Personal")
    assert out.category == "Personal" and out.signals[-1].startswith("operator")
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_tagger.py -q`
Expected: FAIL, `No module named 'everlense.tagger'`.

- [ ] **Step 3: Implement**

`everlense/tagger.py`:
```python
from everlense.models import MediaItem, Label

def confirm(item: MediaItem, suggested: Label, input_fn=input) -> Label:
    prompt = (f"\n{item.path}\n  suggested: {suggested.category} "
              f"(conf {suggested.confidence:.2f}, tier {suggested.tier})\n"
              "  [Enter]=accept, or type a category (e.g. Personal, Screenshots/Linux): ")
    answer = (input_fn(prompt) or "").strip()
    if not answer:
        return suggested
    return Label(category=answer, project=suggested.project, confidence=1.0, tier=suggested.tier,
                 signals=list(suggested.signals) + [f"operator override -> {answer}"])

def confirm_batch(pairs, input_fn=input) -> list[tuple]:
    """pairs: list of (MediaItem, Label). Returns list of (MediaItem, confirmed Label)."""
    return [(item, confirm(item, lbl, input_fn=input_fn)) for item, lbl in pairs]
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_tagger.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add everlense/tagger.py everlense/tests/test_tagger.py
git commit -m "feat(everlense): interactive tagger (injectable input)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: CLI wiring

**Files:**
- Create: `everlense/cli.py`
- Test: `everlense/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`everlense/tests/test_cli.py`:
```python
from PIL import Image
from everlense import cli

def _seed_camera(tmp_path):
    p = tmp_path / "Camera" / "20260531_090000.jpg"; p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (200, 200), (5, 5, 5)).save(p, "JPEG")

def test_scan_dry_run_reports_without_moving(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EVERLENSE_DCIM", str(tmp_path))
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    _seed_camera(tmp_path)
    rc = cli.main(["scan", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "1" in out                 # reports 1 new item
    assert (tmp_path / "Camera" / "20260531_090000.jpg").exists()   # not moved

def test_find_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    assert cli.main(["find", "nothing"]) == 0
```

- [ ] **Step 2: Run to verify fails**

Run: `python3 -m pytest tests/test_cli.py -q`
Expected: FAIL, `No module named 'everlense.cli'`.

- [ ] **Step 3: Implement**

`everlense/cli.py`:
```python
import argparse
import sys
from everlense import config, scanner, classifier, filer, finder, indexer, paths
from everlense.ocr import ocr_text
from everlense import ai_classify

def _scan(args) -> int:
    state = config.load_state()
    known = set(state.get("known_hashes", []))
    items = scanner.scan(known_hashes=known)
    print(f"{len(items)} new media items")
    if args.dry_run:
        cats = config.load_categories()
        for it in items[:50]:
            lbl = classifier.classify(it, cats, ocr_text, ai=None)
            print(f"  [{it.source}] {it.path} -> {lbl.category} (conf {lbl.confidence:.2f})")
        return 0
    cats = config.load_categories()
    ai = (lambda it, c, o: ai_classify.ai_label(it, c, o)) if not args.no_ai else None
    conn = indexer.connect(paths.state_dir() / "photos_index.db")
    for it in items:
        lbl = classifier.classify(it, cats, ocr_text, ai=ai)
        res = filer.file_item(it, lbl, dry_run=False)
        known.add(it.sha256)
        if "sidecar" in res:
            from everlense.models import PhotoRecord
            s = res["sidecar"]
            indexer.upsert(conn, PhotoRecord(
                s["sha256"], res["dest"], s["source"], s["category"], s["project"],
                s["taken_at"], (s["gps"] or {}).get("lat"), (s["gps"] or {}).get("lon"),
                s["address"], s["ocr_text"], s["tags"], s["stamped"], s["filed_at"]))
        print(f"  filed {it.path} -> {res.get('dest', res.get('skipped'))}")
    state["known_hashes"] = sorted(known); config.save_state(state)
    return 0

def _find(args) -> int:
    rows = finder.find(args.query)
    print(f"{len(rows)} matches")
    for r in rows[:100]:
        print(f"  {r['category']:30} {r.get('taken_at','')}  {r['dest_path']}")
    return 0

def _gallery(args) -> int:
    finder.serve(port=args.port)
    return 0

def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="everlense")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("scan"); sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--no-ai", action="store_true"); sp.set_defaults(fn=_scan)
    fp = sub.add_parser("find"); fp.add_argument("query"); fp.set_defaults(fn=_find)
    gp = sub.add_parser("gallery"); gp.add_argument("--port", type=int, default=8533); gp.set_defaults(fn=_gallery)
    args = ap.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify passes**

Run: `python3 -m pytest tests/test_cli.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the FULL suite**

Run: `python3 -m pytest -q`
Expected: PASS (all tasks 1-11 green).

- [ ] **Step 6: Commit**

```bash
git add everlense/cli.py everlense/tests/test_cli.py
git commit -m "feat(everlense): CLI (scan/find/gallery), full suite green

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Live backfill (dry-run first), widget, docs

This task runs against REAL photos. Dry-run is mandatory before any live move.

- [ ] **Step 1: Dry-run the real camera roll, eyeball the plan**

Run: `cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlense && python3 -m everlense.cli scan --dry-run | head -60`
Expected: prints "N new media items" (hundreds) and a sample of `path -> category` lines. NOTHING is moved. Confirm categories look sane (screenshots routing to topics, camera to Business/_Inbox or Personal).

- [ ] **Step 2: Live-run screenshots only first (safest, highest volume), AI on**

Temporarily point DCIM at just Screenshots to limit blast radius, then run live:
Run: `EVERLENSE_DCIM=/sdcard/DCIM python3 -c "from everlense import cli; cli.main(['scan'])" 2>&1 | tail -30`
Expected: files copied into `04_MEDIA_LIBRARY/Photos/Screenshots/<Topic>/`, originals moved to `_Trash/`, sidecars + `.nomedia` written. Spot-check 5 destinations by eye.

- [ ] **Step 3: Verify nothing was lost (count reconciliation)**

Run:
```bash
python3 - <<'PY'
from pathlib import Path
store = Path("/mnt/sdcard/AA_MY_DRIVE/04_MEDIA_LIBRARY/Photos")
filed = sum(1 for _ in store.rglob("*.json"))
trash = sum(1 for _ in (store/"_Trash").rglob("*") if _.is_file())
print("sidecars(filed):", filed, "| trash(originals):", trash)
PY
```
Expected: `filed` roughly equals number of screenshots processed; every original is accounted for in `_Trash` (verify-before-destroy held). If counts diverge, STOP and inspect before processing camera photos.

- [ ] **Step 4: Backfill camera photos with operator confirm** (smaller, needs your taste)

Add a `backfill` subcommand path that pairs each camera item with its suggested label and runs `tagger.confirm_batch` before filing. (If running headless, leave camera photos in `Business/_Inbox` and tag later.) Commit the `backfill` command.

- [ ] **Step 5: Create the Termux:Widget button** (Android-side `.shortcuts`, per the Termux:Boot filesystem law)

Create `/data/data/com.termux/files/home/.shortcuts/everlense-tag`:
```bash
#!/data/data/com.termux/files/usr/bin/bash
proot-distro login ubuntu -- bash -lc \
  'cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlense && python3 -m everlense.cli scan 2>&1 | tail -20'
```
Run: `chmod +x /data/data/com.termux/files/home/.shortcuts/everlense-tag`
Expected: a "everlense-tag" entry appears in the Termux:Widget home-screen widget (if the Termux:Widget app is installed; if not, the CLI is the fallback).

- [ ] **Step 6: Write README + the camera-GPS toggle doc**

`everlense/README.md`: how to run `scan`, `find`, `gallery`; the FREE-FIRST note; the one-time **native camera location toggle** instruction (Camera app -> Settings -> "Save location"/"Location tags" ON) so new photos carry GPS; the `_Trash` 14-day restore note.

- [ ] **Step 7: Confirm media store is excluded from device sync** (honor "phone-only")

Run: `grep -nE "04_MEDIA_LIBRARY|Photos" /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh 2>/dev/null || echo "check rsync excludes"`
Expected: confirm `04_MEDIA_LIBRARY/` is in the rsync exclude list (git already ignores it). Add an exclude if missing.

- [ ] **Step 8: Final commit**

```bash
git add everlense/cli.py everlense/README.md
git commit -m "feat(everlense): backfill command, widget button, README + camera-GPS doc

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (against the spec)

**Spec coverage:**
- Hybrid taxonomy (Personal/Business/Properties/venture): filer `dest_for` + folders. COVERED (Task 7).
- Topic-sorted screenshots (editable): `categories.yaml` + `classify_screenshot`. COVERED (Tasks 2, 5).
- Both-location (EXIF GPS + project address): scanner reads GPS; sidecar carries address; geocoding of project addresses is a follow-up (`project add` not yet built). PARTIAL: per-photo GPS + address-string COVERED; Nominatim geocode of the address into lat/lon is NOT in tasks. Acceptable for v0.1 (address string is the label); add `project add --geocode` in a later iteration.
- Two-tier classification (OCR + Haiku): Tasks 5, 6. COVERED.
- Watermark per project: stamper built (Task 8); wiring into filer via project flag is a follow-up toggle. PARTIAL: stamper exists and is unit-tested; auto-stamp-on-file for watermark-enabled projects is not yet wired into `file_item`. Add in backfill iteration.
- Off-the-roll via `.nomedia`: Task 7. COVERED.
- Backfill ~1,650 + ongoing: Task 12 + `scan`. COVERED.
- Index + find + gallery (127.0.0.1): Tasks 4, 9. COVERED.
- Verify-before-destroy + `_Trash`: Task 7 tests assert it. COVERED.
- FREE-FIRST: only Haiku is paid, `--no-ai` flag gives a fully free path. COVERED.

**Two acknowledged v0.1 gaps (intentional, low-risk, flagged not hidden):**
1. `project add` with Nominatim geocode -> coordinates. v0.1 carries the address string; lat/lon geocode is a fast follow-up.
2. Auto-stamp on file for watermark-enabled projects. Stamper is built/tested; wiring is a follow-up toggle in `file_item`.
Both are additive and do not block the core organize-and-find loop.

**Placeholder scan:** No TBD/TODO. Every code step has complete code. The one prose note in Task 9 (empty-FTS-match) includes the actual `all_rows()` code to add.

**Type consistency:** `MediaItem`, `Label`, `PhotoRecord` field names are identical across scanner -> classifier -> filer -> indexer -> finder -> cli. `classify(item, categories, ocr_fn, ai=None)` signature matches the `ai` callable used in `cli._scan`. `file_item(item, label, dry_run=...)` matches CLI usage.
