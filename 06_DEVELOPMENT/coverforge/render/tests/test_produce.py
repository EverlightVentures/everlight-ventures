# tests/test_produce.py
from render.produce import produce_assets
from render.render_job import BookMeta
from render.image_provider import FakeProvider
from render.bundle import FakeLLM

META = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                vibe="rooftop", trim=(6.0, 9.0), page_count=200,
                paper="white", blurb="Tense.")

def test_paid_produces_render_and_bundle(tmp_path):
    out = produce_assets(META, FakeProvider(), FakeLLM(), str(tmp_path), tier="paid")
    assert out.render.wrap_pdf and out.render.validation_ok
    assert out.bundle is not None and len(out.bundle.keywords) == 7

def test_free_produces_preview_no_bundle(tmp_path):
    out = produce_assets(META, FakeProvider(), FakeLLM(), str(tmp_path), tier="free")
    assert out.render.preview_png and out.render.wrap_pdf is None
    assert out.bundle is None  # bundle is a paid asset
