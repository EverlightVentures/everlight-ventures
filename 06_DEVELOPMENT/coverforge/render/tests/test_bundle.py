# tests/test_bundle.py
from render.bundle import Bundle, build_bundle_prompt, generate_bundle, FakeLLM
from render.render_job import BookMeta

META = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                vibe="rainy rooftop", trim=(6.0, 9.0), page_count=200,
                paper="white", blurb="A tense night.")

def test_prompt_includes_title_genre_and_counts():
    p = build_bundle_prompt(META)
    assert "MIDNIGHT" in p["user"] and "thriller" in p["user"]
    assert "7" in p["system"] and "keyword" in p["system"].lower()
    assert "3" in p["system"] and "categor" in p["system"].lower()

def test_fake_llm_returns_valid_shaped_bundle():
    b = FakeLLM().parse("sys", "user")
    assert isinstance(b, Bundle)
    assert len(b.keywords) == 7
    assert len(b.categories) == 3
    assert len(b.ad_headlines) == 5
    assert b.blurb

def test_generate_bundle_wires_prompt_to_llm():
    b = generate_bundle(META, FakeLLM())
    assert len(b.keywords) == 7 and len(b.categories) == 3
