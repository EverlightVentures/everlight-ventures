# tests/test_integration_fal.py
import os, pytest
from render.render_job import render_book, BookMeta
from render.image_provider import FalFluxProvider

@pytest.mark.skipif(not (os.getenv("COVERFORGE_LIVE") and os.getenv("FAL_KEY")),
                    reason="set COVERFORGE_LIVE=1 + a funded FAL_KEY to run the live Flux test")
def test_real_flux_render(tmp_path):
    meta = BookMeta(title="THE LONG DARK", author="R. Gee", genre="thriller",
                    vibe="neon rain alley", trim=(6.0, 9.0), page_count=240,
                    paper="white", blurb="Nobody walks away clean.")
    result = render_book(meta, FalFluxProvider(os.environ["FAL_KEY"]),
                         str(tmp_path), tier="paid")
    assert result.validation_ok, result.validation_problems
    print("WROTE", result.wrap_pdf)
