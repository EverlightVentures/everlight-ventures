# tests/test_render_job.py
import os
from render.render_job import render_book, BookMeta
from render.image_provider import FakeProvider

def test_render_book_end_to_end_paid(tmp_path):
    meta = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                    vibe="rainy rooftop", trim=(6.0, 9.0), page_count=200,
                    paper="white", blurb="A tense night in the city.")
    result = render_book(meta, FakeProvider(), str(tmp_path), tier="paid")
    assert os.path.exists(result.ebook_pdf)
    assert os.path.exists(result.wrap_pdf)
    assert result.validation_ok, result.validation_problems
    assert result.preview_png is None  # paid tier skips the watermarked preview

def test_render_book_free_tier_makes_preview_only(tmp_path):
    meta = BookMeta(title="MIDNIGHT", author="A. Author", genre="romance",
                    vibe="golden hour", trim=(6.0, 9.0), page_count=120,
                    paper="cream", blurb="Two hearts.")
    result = render_book(meta, FakeProvider(), str(tmp_path), tier="free")
    assert os.path.exists(result.preview_png)
    assert result.wrap_pdf is None  # free tier never produces the print file

def test_render_book_rejects_unknown_tier(tmp_path):
    import pytest
    meta = BookMeta(title="X", author="Y", genre="thriller", vibe="v",
                    trim=(6.0, 9.0), page_count=120, paper="white", blurb="b")
    with pytest.raises(ValueError):
        render_book(meta, FakeProvider(), str(tmp_path), tier="premium")
