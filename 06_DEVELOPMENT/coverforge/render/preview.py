# render/preview.py
"""Free-tier output: small, watermarked PNG. The paywall sits on the download
of the full-res print file, so generating this preview is cheap to give away."""
from PIL import Image, ImageDraw, ImageFont

def make_preview(front: Image.Image, max_w: int = 600, text: str = "COVERFORGE PREVIEW") -> Image.Image:
    scale = max_w / front.width
    prev = front.convert("RGB").resize((max_w, round(front.height * scale)))
    draw = ImageDraw.Draw(prev, "RGBA")
    font = ImageFont.load_default()
    # repeat a faint diagonal watermark across the image
    for y in range(0, prev.height, 120):
        for x in range(-100, prev.width, 240):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 90))
    return prev
