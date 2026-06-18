"""
Generate ebook covers for KDP from existing square DALL-E 3 cover art.

Amazon KDP Ebook Cover Specs:
- Ideal: 1600 x 2560 px (width x height), ratio 1:1.6
- Format: JPEG or TIFF
- RGB color space
- Max 50 MB

Layout:
- Top band: series name
- Center: cover art (scaled to fill width)
- Bottom band: title + "Book N of 5" + author/publisher
- Background: themed color per book
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from shared.publishing.book_config import BOOKS as BOOK_REGISTRY, BASE_DIR
from shared.publishing.image_utils import draw_centered_text, create_gradient_band

# Amazon ideal ebook cover size
EBOOK_W = 1600
EBOOK_H = 2560

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/tuffy/tuffy_bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/tuffy/tuffy_regular.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/tuffy/tuffy_italic.ttf"

# Build BOOKS dict from central registry (previously duplicated inline)
_TITLE_SPLITS = {1: "Sam's First\nSuperpower", 2: "Sam's Second\nSuperpower",
                 3: "Sam's Third\nSuperpower", 4: "Sam's Fourth\nSuperpower",
                 5: "Sam's Fifth\nSuperpower"}
BOOKS = {}
for _bid in [1, 2, 3, 4, 5]:
    _b = BOOK_REGISTRY[_bid]
    BOOKS[str(_bid)] = {
        "cover_jpg": _b["cover_jpg"],
        "ebook_cover": _b["img_dir"] / f"{_b['prefix']}_cover_ebook.jpg",
        "title": _TITLE_SPLITS[_bid],
        "title_short": _b["title"],
        "book_num": _bid,
        "bg_top": _b["ebook_bg_top"],
        "bg_bottom": _b["ebook_bg_bottom"],
        "accent": _b["accent"],
    }


# draw_centered_text and create_gradient_band are now imported from
# shared.publishing.image_utils


def build_ebook_cover(config):
    """Build a portrait ebook cover from existing square art."""
    print(f"\n--- Book {config['book_num']}: {config['title_short']} ---")

    if not config["cover_jpg"].exists():
        print(f"  ERROR: Source cover not found: {config['cover_jpg']}")
        return False

    # Load source art
    art = Image.open(config["cover_jpg"]).convert("RGB")
    print(f"  Source: {art.size[0]}x{art.size[1]}")

    # Create gradient background
    canvas = create_gradient_band(EBOOK_W, EBOOK_H, config["bg_top"], config["bg_bottom"])
    draw = ImageDraw.Draw(canvas)

    # Load fonts
    series_font = ImageFont.truetype(FONT_BOLD, 48)
    title_font = ImageFont.truetype(FONT_BOLD, 90)
    book_num_font = ImageFont.truetype(FONT_BOLD, 40)
    author_font = ImageFont.truetype(FONT_REG, 36)
    tagline_font = ImageFont.truetype(FONT_ITALIC, 30)

    accent = config["accent"]
    white = (255, 255, 255)

    # --- TOP SECTION ---
    y = 60

    # Series name
    draw_centered_text(draw, "ADVENTURES WITH SAM AND ROBO", y, series_font, accent, EBOOK_W)
    y += 70

    # Accent line
    line_w = 400
    line_x = (EBOOK_W - line_w) // 2
    draw.line([(line_x, y), (line_x + line_w, y)], fill=accent, width=3)
    y += 30

    # Title (multi-line)
    title_lines = config["title"].split("\n")
    for line in title_lines:
        draw_centered_text(draw, line, y, title_font, white, EBOOK_W)
        y += 105
    y += 10

    # Accent line
    draw.line([(line_x, y), (line_x + line_w, y)], fill=accent, width=3)
    y += 40

    # --- CENTER: COVER ART ---
    # Scale art to fit width with some padding
    art_padding = 80
    art_width = EBOOK_W - (art_padding * 2)
    scale = art_width / art.width
    art_height = int(art.height * scale)
    art_resized = art.resize((art_width, art_height), Image.LANCZOS)
    art_resized = art_resized.filter(ImageFilter.SHARPEN)

    # Add rounded corner effect by placing on gradient
    art_x = art_padding
    art_y = y
    canvas.paste(art_resized, (art_x, art_y))

    # Thin border around art
    draw.rectangle(
        [art_x - 2, art_y - 2, art_x + art_width + 2, art_y + art_height + 2],
        outline=accent,
        width=3,
    )

    y = art_y + art_height + 40

    # --- BOTTOM SECTION ---
    # Book number
    draw_centered_text(draw, f"Book {config['book_num']} of 5", y, book_num_font, accent, EBOOK_W)
    y += 60

    # Author/Publisher
    draw_centered_text(draw, "Everlight Kids", y, author_font, white, EBOOK_W)
    y += 50

    # Tagline
    draw_centered_text(
        draw,
        '"Every word is a door. And every door is an adventure."',
        y,
        tagline_font,
        (180, 180, 180),
        EBOOK_W,
    )

    # Save
    config["ebook_cover"].parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(config["ebook_cover"]), "JPEG", quality=95, dpi=(300, 300))

    size_kb = os.path.getsize(config["ebook_cover"]) // 1024
    print(f"  Saved: {config['ebook_cover']}")
    print(f"  Size: {size_kb} KB | {EBOOK_W}x{EBOOK_H} px")
    return True


def main():
    print("=" * 60)
    print("KDP EBOOK COVER GENERATOR")
    print(f"Target: {EBOOK_W}x{EBOOK_H} px (Amazon ideal)")
    print("=" * 60)

    results = []
    for book_id, config in BOOKS.items():
        ok = build_ebook_cover(config)
        results.append((book_id, config["title_short"], ok))

    print("\n" + "=" * 60)
    print("RESULTS:")
    for book_id, title, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  Book {book_id}: {title} -- {status}")
    print("=" * 60)
    print("Upload ebook covers: KDP Ebook -> Book Cover -> Upload")
    print("Upload paperback covers: KDP Paperback -> Cover -> Upload")


if __name__ == "__main__":
    main()
