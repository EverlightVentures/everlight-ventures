"""
Shared image manipulation utilities for the publishing pipeline.

Consolidates duplicated functions from:
  - build_books.py::compress_image
  - embed_images.py::compress_and_encode
  - build_cover_pdfs.py::draw_centered_text, draw_wrapped_text
  - build_ebook_covers.py::draw_centered_text, create_gradient_bg, create_gradient_band
"""

import base64
from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


def compress_image(
    img_path: str,
    max_width: int = 1200,
    quality: int = 85,
) -> bytes:
    """Resize image to max_width (preserving aspect ratio) and JPEG-compress.

    Returns raw JPEG bytes.
    """
    img = Image.open(img_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if w > max_width:
        ratio = max_width / w
        img = img.resize((max_width, int(h * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def compress_and_encode(
    img_path: str,
    max_width: int = 800,
    quality: int = 72,
) -> str:
    """Compress image and return a base64 data-URI string."""
    data = compress_image(img_path, max_width=max_width, quality=quality)
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    canvas_width: int,
) -> int:
    """Draw text centered horizontally on the canvas. Returns text height."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (canvas_width - text_w) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return text_h


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    line_spacing: float = 1.3,
) -> int:
    """Draw word-wrapped text. Returns the final Y position after all text."""
    paragraphs = text.split("\n")
    current_y = y
    for para in paragraphs:
        if not para.strip():
            current_y += int(font.size * line_spacing)
            continue
        words = para.split()
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > max_width and line:
                draw.text((x, current_y), line, font=font, fill=fill)
                current_y += int((bbox[3] - bbox[1]) * line_spacing)
                line = word
            else:
                line = test_line
        if line:
            bbox = draw.textbbox((0, 0), line, font=font)
            draw.text((x, current_y), line, font=font, fill=fill)
            current_y += int((bbox[3] - bbox[1]) * line_spacing)
    return current_y


def create_gradient_band(
    width: int,
    height: int,
    color_top: Tuple[int, int, int],
    color_bottom: Tuple[int, int, int],
) -> Image.Image:
    """Create a vertical gradient image using line drawing (efficient)."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y_pos in range(height):
        ratio = y_pos / max(height - 1, 1)
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        draw.line([(0, y_pos), (width - 1, y_pos)], fill=(r, g, b))
    return img
