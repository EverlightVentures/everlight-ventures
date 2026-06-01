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
