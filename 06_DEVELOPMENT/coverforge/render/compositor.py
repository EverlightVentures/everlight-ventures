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

def compose_wrap(background: Image.Image, title: str, author: str,
                 blurb: str, dims, font_path=None) -> Image.Image:
    """Assemble back | spine | front into one full-bleed wrap at exact pixel size."""
    wrap = background.convert("RGB").resize((dims.full_w_px, dims.full_h_px))
    draw = ImageDraw.Draw(wrap)
    # front panel: composite the finished front into the rightmost panel
    front = compose_front(background, title, author,
                          (dims.front_w_px, dims.full_h_px), font_path)
    wrap.paste(front, (dims.back_w_px + dims.spine_px, 0))
    # back panel: blurb text, wrapped within the back panel margins
    bmargin = int(dims.back_w_px * 0.10)
    bfont = _load_font(font_path, int(dims.full_h_px * 0.025))
    _draw_wrapped(draw, blurb, (bmargin, int(dims.full_h_px * 0.15)),
                  dims.back_w_px - 2 * bmargin, bfont)
    # spine: title rotated 90deg, only if spine is wide enough for legible text
    if dims.spine_px >= 60:
        _draw_spine(wrap, title, dims, font_path)
    return wrap

def _draw_wrapped(draw, text, xy, max_w, font):
    x, y = xy
    line, words = "", text.split()
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            draw.text((x, y), line, font=font, fill=(235, 235, 235))
            y += int(font.size * 1.4) if hasattr(font, "size") else 16
            line = word
    if line:
        draw.text((x, y), line, font=font, fill=(235, 235, 235))

def _draw_spine(wrap, title, dims, font_path):
    strip = Image.new("RGB", (dims.full_h_px, dims.spine_px), (0, 0, 0))
    sdraw = ImageDraw.Draw(strip)
    sfont = _fit_text(sdraw, title, dims.full_h_px - 40, font_path, int(dims.spine_px * 0.5))
    tw = sdraw.textlength(title, font=sfont)
    sdraw.text(((dims.full_h_px - tw) / 2, dims.spine_px * 0.2), title,
               font=sfont, fill=(255, 255, 255))
    wrap.paste(strip.rotate(90, expand=True), (dims.back_w_px, 0))
