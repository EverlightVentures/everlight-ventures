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

def _src_named(tmp_path, folder, name, color):
    p = tmp_path / folder / name; p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color).save(p, "JPEG")
    return MediaItem(str(p), scanner.sha256_file(p), "camera", "2026-05-31T10:10:10", None, 64, 64)

def test_same_basename_distinct_photos_both_survive(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    a = _src_named(tmp_path, "Camera", "20260531_101010.jpg", (10, 20, 30))
    b = _src_named(tmp_path, "WhatsApp", "20260531_101010.jpg", (200, 100, 50))
    assert a.sha256 != b.sha256
    ra = filer.file_item(a, Label(category="Personal"), dry_run=False)
    rb = filer.file_item(b, Label(category="Personal"), dry_run=False)
    assert Path(ra["dest"]) != Path(rb["dest"])                 # distinct dest, no overwrite
    assert scanner.sha256_file(Path(ra["dest"])) == a.sha256
    assert scanner.sha256_file(Path(rb["dest"])) == b.sha256
    trashed = list((tmp_path / "store" / "_Trash").glob("*.jpg"))
    assert len(trashed) == 2                                     # BOTH originals survive in trash

def test_refile_same_hash_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    item = _src_named(tmp_path, "Camera", "x.jpg", (5, 5, 5))
    filer.file_item(item, Label(category="Personal"), dry_run=False)
    # re-create the same-content original and file again
    item2 = _src_named(tmp_path, "Camera", "x.jpg", (5, 5, 5))
    res = filer.file_item(item2, Label(category="Personal"), dry_run=False)
    assert res.get("state") == "already_filed"
    dests = list((tmp_path / "store" / "Personal").rglob("*.jpg"))
    assert len(dests) == 1                                       # no duplicate filed

def test_hash_mismatch_aborts_and_keeps_original(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path / "store"))
    item = _src_named(tmp_path, "Camera", "y.jpg", (9, 9, 9))
    item.sha256 = "deadbeef" * 8                                 # force verify failure
    with pytest.raises(RuntimeError):
        filer.file_item(item, Label(category="Personal"), dry_run=False)
    assert Path(item.path).exists()                             # original untouched
    assert not list((tmp_path / "store").rglob("*.part"))       # no leftover temp
