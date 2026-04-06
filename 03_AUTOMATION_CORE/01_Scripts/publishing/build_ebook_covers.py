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
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

BASE_DIR = Path(
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM"
)

# Amazon ideal ebook cover size
EBOOK_W = 1600
EBOOK_H = 2560

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/tuffy/tuffy_bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/tuffy/tuffy_regular.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/tuffy/tuffy_italic.ttf"

BOOKS = {
    "1": {
        "cover_jpg": BASE_DIR / "Book1" / "images" / "1_cover.jpg",
        "ebook_cover": BASE_DIR / "Book1" / "images" / "1_cover_ebook.jpg",
        "title": "Sam's First\nSuperpower",
        "title_short": "Sam's First Superpower",
        "book_num": 1,
        "bg_top": (30, 60, 100),
        "bg_bottom": (20, 45, 75),
        "accent": (218, 165, 32),
    },
    "2": {
        "cover_jpg": BASE_DIR / "Book 2" / "images" / "2_cover.jpg",
        "ebook_cover": BASE_DIR / "Book 2" / "images" / "2_cover_ebook.jpg",
        "title": "Sam's Second\nSuperpower",
        "title_short": "Sam's Second Superpower",
        "book_num": 2,
        "bg_top": (15, 40, 90),
        "bg_bottom": (10, 30, 70),
        "accent": (80, 180, 255),
    },
    "3": {
        "cover_jpg": BASE_DIR / "book_3" / "images" / "3_cover.jpg",
        "ebook_cover": BASE_DIR / "book_3" / "images" / "3_cover_ebook.jpg",
        "title": "Sam's Third\nSuperpower",
        "title_short": "Sam's Third Superpower",
        "book_num": 3,
        "bg_top": (50, 20, 80),
        "bg_bottom": (35, 10, 60),
        "accent": (180, 120, 255),
    },
    "4": {
        "cover_jpg": BASE_DIR / "book_4" / "images" / "4_cover.jpg",
        "ebook_cover": BASE_DIR / "book_4" / "images" / "4_cover_ebook.jpg",
        "title": "Sam's Fourth\nSuperpower",
        "title_short": "Sam's Fourth Superpower",
        "book_num": 4,
        "bg_top": (15, 60, 30),
        "bg_bottom": (10, 45, 20),
        "accent": (80, 200, 100),
    },
    "5": {
        "cover_jpg": BASE_DIR / "book_5" / "images" / "5_cover.jpg",
        "ebook_cover": BASE_DIR / "book_5" / "images" / "5_cover_ebook.jpg",
        "title": "Sam's Fifth\nSuperpower",
        "title_short": "Sam's Fifth Superpower",
        "book_num": 5,
        "bg_top": (90, 45, 10),
        "bg_bottom": (70, 35, 8),
        "accent": (255, 180, 60),
    },
}


def draw_centered_text(draw, text, y, font, fill, canvas_width):
    """Draw text centered horizontally."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (canvas_width - text_w) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def create_gradient_bg(width, height, color_top, color_bottom):
    """Create a vertical gradient background."""
    img = Image.new("RGB", (width, height))
    for y in range(height):
        ratio = y / height
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    return img


def create_gradient_band(width, height, color_top, color_bottom):
    """Create a gradient band more efficiently using line drawing."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
        g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
        b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
        draw.line([(0, y), (width - 1, y)], fill=(r, g, b))
    return img


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
