from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_GOLD = (212, 175, 55)        # Everlight gold #D4AF37
_BG = (10, 10, 10)

def _font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except Exception:
        return ImageFont.load_default()

def stamp(src: str, fields: list[str]) -> str:
    src_p = Path(src)
    out_dir = src_p.parent / "_stamped"; out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (src_p.stem + "_stamped" + src_p.suffix)
    with Image.open(src).convert("RGB") as im:
        w, h = im.size
        draw = ImageDraw.Draw(im, "RGBA")
        size = max(14, w // 45)
        font = _font(size)
        text = "  |  ".join(f for f in fields if f)
        pad = size // 2
        band_h = size + 2 * pad
        draw.rectangle([(0, h - band_h), (w, h)], fill=(*_BG, 180))
        draw.text((pad, h - band_h + pad), text, font=font, fill=_GOLD)
        im.save(out, "JPEG", quality=90)
    return str(out)
