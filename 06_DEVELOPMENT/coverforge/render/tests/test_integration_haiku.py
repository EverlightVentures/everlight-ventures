# tests/test_integration_haiku.py
import os, pytest
from render.bundle import HaikuLLM, generate_bundle
from render.render_job import BookMeta

@pytest.mark.skipif(not (os.getenv("COVERFORGE_LIVE") and os.getenv("ANTHROPIC_API_KEY")),
                    reason="set COVERFORGE_LIVE=1 + a funded ANTHROPIC_API_KEY to run the live Haiku test")
def test_real_haiku_bundle():
    meta = BookMeta(title="THE LONG DARK", author="R. Gee", genre="thriller",
                    vibe="neon rain alley", trim=(6.0, 9.0), page_count=240,
                    paper="white", blurb="Nobody walks away clean.")
    b = generate_bundle(meta, HaikuLLM(os.environ["ANTHROPIC_API_KEY"]))
    assert len(b.keywords) == 7 and len(b.categories) == 3 and len(b.ad_headlines) == 5
    print("BLURB:", b.blurb)
