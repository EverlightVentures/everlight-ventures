# render/compositor.py
"""Composite real typography over a background. Pillow renders true fonts,
so titles are legible and reproducible (the product's core differentiator)."""
from PIL import Image, ImageDraw, ImageFont

def _load_font(font_path, size):
    if font_path:
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()  # tests stay font-agnostic and deterministic

def _fit_text(draw, text, max_w, font_path, start_size):
    size = start_size
    while size > 8:
        font = _load_font(font_path, size)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 2
    return _load_font(font_path, 8)

def compose_front(background: Image.Image, title: str, author: str,
                  target_size, font_path=None) -> Image.Image:
    img = background.convert("RGB").resize(target_size)
    draw = ImageDraw.Draw(img)
    w, h = target_size
    margin = int(w * 0.08)
    title_font = _fit_text(draw, title, w - 2 * margin, font_path, int(h * 0.10))
    author_font = _fit_text(draw, author, w - 2 * margin, font_path, int(h * 0.05))
    # title upper third, author lower margin, both centred
    tw = draw.textlength(title, font=title_font)
    draw.text(((w - tw) / 2, h * 0.12), title, font=title_font, fill=(255, 255, 255))
    aw = draw.textlength(author, font=author_font)
    draw.text(((w - aw) / 2, h * 0.85), author, font=author_font, fill=(245, 245, 245))
    return img
