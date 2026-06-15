# tests/test_prompt_builder.py
import pytest
from render.prompt_builder import build_background_prompt, SUPPORTED_GENRES

def test_supported_genres_are_the_three_seeded():
    assert SUPPORTED_GENRES == ("romance", "thriller", "fantasy")

def test_prompt_includes_genre_styling_and_bans_text():
    p = build_background_prompt("thriller", vibe="rainy city rooftop")
    assert "rainy city rooftop" in p
    assert "no text" in p.lower()
    assert "thriller" in p.lower() or "noir" in p.lower()

def test_unknown_genre_falls_back_but_still_bans_text():
    p = build_background_prompt("western", vibe="desert")
    assert "no text" in p.lower()
    assert "desert" in p
