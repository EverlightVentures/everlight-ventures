# render/prompt_builder.py
"""Genre -> background-image prompt. The image must contain NO text;
typography is composited later, so we explicitly forbid lettering."""

SUPPORTED_GENRES = ("romance", "thriller", "fantasy")

_GENRE_STYLE = {
    "romance": "warm cinematic romance book-cover art, soft golden light, intimate mood",
    "thriller": "dark noir thriller book-cover art, high contrast, tense moody atmosphere",
    "fantasy": "epic fantasy book-cover art, dramatic lighting, painterly detail",
}
_NO_TEXT = "no text, no letters, no title, no typography, no watermark, leave clear space for a title"

def build_background_prompt(genre: str, vibe: str) -> str:
    style = _GENRE_STYLE.get(genre.lower(), "cinematic book-cover background art")
    return f"{style}, {vibe}, vertical book cover composition, {_NO_TEXT}"
