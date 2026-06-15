# tests/test_image_provider.py
from render.image_provider import FakeProvider

def test_fake_provider_returns_exact_size_rgb():
    img = FakeProvider().generate("anything", 800, 1200)
    assert img.size == (800, 1200)
    assert img.mode == "RGB"

def test_fake_provider_is_deterministic_for_same_prompt():
    a = FakeProvider().generate("same", 64, 64)
    b = FakeProvider().generate("same", 64, 64)
    assert a.tobytes() == b.tobytes()

def test_fake_provider_varies_with_prompt():
    a = FakeProvider().generate("one", 64, 64)
    b = FakeProvider().generate("two", 64, 64)
    assert a.tobytes() != b.tobytes()
