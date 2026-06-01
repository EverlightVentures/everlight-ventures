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
