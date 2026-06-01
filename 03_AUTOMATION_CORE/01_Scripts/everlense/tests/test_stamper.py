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
