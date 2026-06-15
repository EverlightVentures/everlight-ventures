# tests/test_preview.py
from PIL import Image
from render.preview import make_preview

def test_preview_is_downscaled_and_changed():
    full = Image.new("RGB", (1800, 2700), (50, 50, 50))
    prev = make_preview(full, max_w=600)
    assert prev.width == 600
    assert prev.height == 900  # aspect preserved
    assert prev.tobytes() != Image.new("RGB", (600, 900), (50, 50, 50)).tobytes()  # watermark drawn
