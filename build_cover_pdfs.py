"""
Generate full-wrap print-ready cover PDFs for KDP paperback.
v3 -- Safe-zone compliant. No text within 0.50" of trim edges.

Layout: [left bleed | BACK COVER | SPINE | FRONT COVER | right bleed]

KDP dimensions: 12.360 x 9.250 inches
Trim: 6 x 9", cream paper, ~44 pages, 0.110" spine.

FRONT: Dark background + cover art INSET inside safe zone
       (baked-in title text stays 0.55" from outer edges)
SPINE: Colored strip (no text -- too thin)
BACK:  Solid color + text only (NO cover art), all text inside safe zone
"""

import os
import requests
import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

API_KEY = os.environ.get(
    "OPENAI_API_KEY",
    "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",
)
BASE_DIR = Path(
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/"
    "Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM"
)

# ---- KDP COVER DIMENSIONS (v3) ----
TOTAL_W_IN = 12.360   # updated from 12.353
TOTAL_H_IN = 9.250
DPI = 300
TOTAL_W_PX = round(TOTAL_W_IN * DPI)  # 3708
TOTAL_H_PX = round(TOTAL_H_IN * DPI)  # 2775

BLEED = 0.125
TRIM_W = 6.0
TRIM_H = 9.0
SPINE_W_IN = TOTAL_W_IN - (2 * BLEED) - (2 * TRIM_W)  # ~0.110"

BLEED_PX = round(BLEED * DPI)                                      # 38
TRIM_W_PX = round(TRIM_W * DPI)                                    # 1800
SPINE_W_PX = TOTAL_W_PX - (2 * BLEED_PX) - (2 * TRIM_W_PX)       # 32

FRONT_X = BLEED_PX + TRIM_W_PX + SPINE_W_PX   # where front starts
FRONT_W = TRIM_W_PX + BLEED_PX                 # front width incl bleed
BACK_W = BLEED_PX + TRIM_W_PX                  # back width incl bleed

# Safe zone: 0.55" from outer file edge (exceeds KDP min of 0.50")
SAFE_PX = round(0.55 * DPI)  # 165px

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/tuffy/tuffy_bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/tuffy/tuffy_regular.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/tuffy/tuffy_italic.ttf"

BOOKS = {
    "1": {
        "cover_jpg": BASE_DIR / "Book1" / "images" / "1_cover.jpg",
        "cover_pdf": BASE_DIR / "Book1" / "images" / "1_cover_print.pdf",
        "title": "Sam's First Superpower",
        "book_num": 1,
        "spine_color": (218, 165, 32),
        "front_bg": (25, 35, 55),
        "back_bg": (255, 248, 220),
        "back_text_color": (60, 40, 10),
        "accent": (218, 165, 32),
        "back_copy": (
            "Sam was a curious boy who loved adventures. He loved climbing "
            "trees, asking questions, and finding things nobody else noticed.\n\n"
            "So when he discovered a glowing book beneath an old oak tree, he "
            "did what any curious kid would do -- he opened it.\n\n"
            "Out popped Robo. A small, friendly robot with big kind eyes and a "
            "glowing display screen. Robo was here to teach Sam about words, "
            "sounds, and the power of showing up for others.\n\n"
            "Together they rescued a scared cat, fed a hungry rabbit, comforted "
            "a sad puppy, calmed an angry bird, and helped an old farmer earn "
            "an honest reward.\n\n"
            "An interactive coloring book and story hybrid where every left "
            "page is a B&W illustration for coloring and every right page "
            "shows the same scene in full color."
        ),
    },
    "2": {
        "cover_jpg": BASE_DIR / "Book 2" / "images" / "2_cover.jpg",
        "cover_pdf": BASE_DIR / "Book 2" / "images" / "2_cover_print.pdf",
        "title": "Sam's Second Superpower",
        "book_num": 2,
        "spine_color": (30, 100, 200),
        "front_bg": (10, 25, 60),
        "back_bg": (230, 240, 255),
        "back_text_color": (15, 30, 60),
        "accent": (80, 180, 255),
        "back_copy": (
            "Sam learned to talk to animals. Now it is time to think like "
            "a scientist.\n\n"
            "When Robo reveals a surprise invitation to the local science lab, "
            "Sam grabs his backpack and heads straight for the bubbling beakers, "
            "growing plants, and experiments waiting for a curious mind.\n\n"
            "Inside the lab, Sam discovers compound words -- two small words "
            "that snap together to make one big one: backpack, sunflower, "
            "rainbow, starfish. He builds a baking soda volcano that actually "
            "erupts. He plants a seed and watches it push through the soil.\n\n"
            "Interactive coloring book hybrid. Phonics progression. "
            "STEM concepts. Values that stick."
        ),
    },
    "3": {
        "cover_jpg": BASE_DIR / "book_3" / "images" / "3_cover.jpg",
        "cover_pdf": BASE_DIR / "book_3" / "images" / "3_cover_print.pdf",
        "title": "Sam's Third Superpower",
        "book_num": 3,
        "spine_color": (100, 40, 150),
        "front_bg": (30, 10, 50),
        "back_bg": (245, 235, 255),
        "back_text_color": (35, 15, 55),
        "accent": (180, 120, 255),
        "generate_prompt": (
            "Children's book cover for 'Sam's Third Superpower'. "
            "Sam, a 6-7 year old boy with messy spiky brown hair and red t-shirt, "
            "holding a mysterious note with glowing letters, looking excited. "
            "His compact silver robot companion Robo beside him with glowing blue LED eyes. "
            "Background: magical trail through a sunny park with floating letters, "
            "a sparkling stream, and treasure chest partially visible. "
            "Title space at top. 3D Disney/Pixar animation style, vibrant, "
            "cinematic lighting, warm adventure atmosphere."
        ),
        "back_copy": (
            "A mysterious note appears inside the magical book. It is the "
            "first clue in a scavenger hunt that will test everything Sam "
            "has learned.\n\n"
            "With Robo by his side, Sam follows the trail across his "
            "neighborhood -- listening for sounds others miss, noticing "
            "details hidden in plain sight, and solving clues woven from "
            "blends and digraphs: sh, ch, th, bl, cr, st.\n\n"
            "Each clue sharpens Sam's senses. He hears a friend calling "
            "for help before anyone else does. He spots a hidden path that "
            "was invisible a moment ago.\n\n"
            "Interactive coloring book hybrid. Phonics progression. "
            "Mystery and problem-solving. Values that stick."
        ),
    },
    "4": {
        "cover_jpg": BASE_DIR / "book_4" / "images" / "4_cover.jpg",
        "cover_pdf": BASE_DIR / "book_4" / "images" / "4_cover_print.pdf",
        "title": "Sam's Fourth Superpower",
        "book_num": 4,
        "spine_color": (34, 139, 34),
        "front_bg": (10, 40, 15),
        "back_bg": (230, 250, 230),
        "back_text_color": (15, 45, 15),
        "accent": (80, 200, 100),
        "back_copy": (
            "Sam noticed the river was sick.\n\n"
            "Trash on the banks. Murky water. A patient heron waiting for "
            "things to be clean again. And once Sam noticed something, he "
            "could not un-notice it.\n\n"
            "With his robot best friend Robo, his friend Lily, and the help "
            "of wise mentors like Mr. Green, Farmer Brown, and Ranger Jane, "
            "Sam sets out to learn everything he can about protecting the "
            "planet -- from recycling and water conservation to planting "
            "trees and defending wildlife habitats.\n\n"
            "An interactive adventure and coloring book that teaches "
            "environmental responsibility, STEM concepts, and timeless "
            "values through a story kids love."
        ),
    },
    "5": {
        "cover_jpg": BASE_DIR / "book_5" / "images" / "5_cover.jpg",
        "cover_pdf": BASE_DIR / "book_5" / "images" / "5_cover_print.pdf",
        "title": "Sam's Fifth Superpower",
        "book_num": 5,
        "spine_color": (220, 120, 30),
        "front_bg": (55, 25, 5),
        "back_bg": (255, 245, 230),
        "back_text_color": (60, 30, 10),
        "accent": (255, 180, 60),
        "back_copy": (
            "Sam has four superpowers. But the fifth -- and greatest -- "
            "has been inside him all along.\n\n"
            "When five younger kids who are struggling to read need someone "
            "who has been where they are, Sam steps up. He teaches them "
            "phonics through adventure -- hunting compound words in the "
            "park, building a birdhouse, and saving a community garden "
            "using ALL FOUR of his superpowers.\n\n"
            "But the real magic is watching the kids discover their own "
            "powers. And when Jax picks up a book and reads his first "
            "page out loud, Sam feels something deeper than any superpower "
            "he has ever earned.\n\n"
            "Then Grandma arrives. And reveals a secret that changes "
            "everything Sam thought he knew about the magical book.\n\n"
            "The epic conclusion to Adventures with Sam and Robo."
        ),
    },
}

STYLE_GUIDE = (
    "STYLE: 3D digital animation style, high-quality, Disney/Pixar aesthetic, "
    "cinematic lighting, vibrant and saturated colors. "
    "CHARACTERS: Sam: 6-7 years old boy, messy spiky brown hair, large "
    "expressive brown eyes, energetic posture, wearing a red t-shirt. "
    "Robo: Friendly rounded silver/white robot companion, compact size, "
    "big glowing blue LED eyes, chest display screen."
)


def generate_cover_image(prompt, save_path):
    """Generate a cover via DALL-E 3."""
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    full_prompt = (
        "Vibrant 3D animation style children's book cover illustration, "
        f"cinematic lighting, rich textures, soft depth of field. {prompt}. "
        f"{STYLE_GUIDE}"
    )
    data = {
        "model": "dall-e-3",
        "prompt": full_prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "hd",
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  Generating cover (attempt {attempt + 1})...")
            resp = requests.post(url, headers=headers, json=data, timeout=120)
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]
            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(img_resp.content)
            print(f"  Saved: {save_path}")
            return True
        except Exception as e:
            print(f"  Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    return False


def draw_centered_text(draw, text, y, font, fill, canvas_width):
    """Draw text centered horizontally. Returns text height."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (canvas_width - text_w) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return text_h


def draw_wrapped_text(draw, text, x, y, max_width, font, fill, line_spacing=1.3):
    """Draw word-wrapped text. Returns final Y position."""
    paragraphs = text.split("\n")
    current_y = y
    for para in paragraphs:
        if para.strip() == "":
            current_y += int(font.size * 0.6)
            continue
        words = para.split()
        lines = []
        current_line = ""
        for word in words:
            test = (current_line + " " + word).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)
        for line in lines:
            draw.text((x, current_y), line, font=font, fill=fill)
            current_y += int(font.size * line_spacing)
    return current_y


def build_full_wrap(config):
    """Build a safe-zone compliant full-wrap cover PDF."""
    print(f"\n--- Book {config['book_num']}: {config['title']} ---")

    # Ensure front cover JPEG exists
    if not config["cover_jpg"].exists():
        if "generate_prompt" in config:
            print("  Cover JPEG missing -- generating via DALL-E 3...")
            ok = generate_cover_image(
                config["generate_prompt"], config["cover_jpg"]
            )
            if not ok:
                print("  FAILED to generate cover. Skipping.")
                return False
        else:
            print(f"  ERROR: Cover not found: {config['cover_jpg']}")
            return False

    front_art = Image.open(config["cover_jpg"]).convert("RGB")

    # Create canvas -- fill with back cover color
    canvas = Image.new("RGB", (TOTAL_W_PX, TOTAL_H_PX), config["back_bg"])
    draw = ImageDraw.Draw(canvas)

    # ========================================
    # FRONT COVER -- dark bg + inset art
    # ========================================
    # Fill entire front area with dark background (bleeds to all edges)
    draw.rectangle(
        [FRONT_X, 0, TOTAL_W_PX, TOTAL_H_PX],
        fill=config["front_bg"],
    )

    # Art inset boundaries (all text stays inside safe zone)
    art_left = FRONT_X + 30          # small gap from spine
    art_right = TOTAL_W_PX - SAFE_PX  # 0.55" from right edge
    art_top = SAFE_PX + 80            # safe zone + room for series name
    art_bottom = TOTAL_H_PX - SAFE_PX - 70  # safe zone + room for footer

    art_area_w = art_right - art_left
    art_area_h = art_bottom - art_top

    # Scale art to fill width, center vertically
    scale = art_area_w / front_art.width
    scaled_w = art_area_w
    scaled_h = round(front_art.height * scale)

    if scaled_h > art_area_h:
        # If too tall, scale to fill height instead and center horizontally
        scale = art_area_h / front_art.height
        scaled_h = art_area_h
        scaled_w = round(front_art.width * scale)

    art_resized = front_art.resize((scaled_w, scaled_h), Image.LANCZOS)
    art_resized = art_resized.filter(ImageFilter.SHARPEN)

    # Center art in the available area
    paste_x = art_left + (art_area_w - scaled_w) // 2
    paste_y = art_top + (art_area_h - scaled_h) // 2

    canvas.paste(art_resized, (paste_x, paste_y))

    # Thin accent border around the art
    draw.rectangle(
        [paste_x - 3, paste_y - 3,
         paste_x + scaled_w + 3, paste_y + scaled_h + 3],
        outline=config["accent"],
        width=3,
    )

    # Front cover text -- series name above art (inside safe zone)
    front_series_font = ImageFont.truetype(FONT_BOLD, 36)
    front_footer_font = ImageFont.truetype(FONT_REG, 28)

    # Center series name in front cover area
    series_text = "ADVENTURES WITH SAM AND ROBO"
    bbox = draw.textbbox((0, 0), series_text, font=front_series_font)
    text_w = bbox[2] - bbox[0]
    front_center_x = FRONT_X + FRONT_W // 2
    draw.text(
        (front_center_x - text_w // 2, SAFE_PX + 15),
        series_text,
        font=front_series_font,
        fill=config["accent"],
    )

    # Footer below art
    footer_text = f"Book {config['book_num']} of 5  |  Everlight Kids"
    bbox = draw.textbbox((0, 0), footer_text, font=front_footer_font)
    text_w = bbox[2] - bbox[0]
    draw.text(
        (front_center_x - text_w // 2, TOTAL_H_PX - SAFE_PX - 30),
        footer_text,
        font=front_footer_font,
        fill=(200, 200, 200),
    )

    # ========================================
    # SPINE -- colored strip
    # ========================================
    spine_x = BLEED_PX + TRIM_W_PX
    draw.rectangle(
        [spine_x, 0, spine_x + SPINE_W_PX, TOTAL_H_PX],
        fill=config["spine_color"],
    )

    # ========================================
    # BACK COVER -- solid color + text only
    # ========================================
    # Back bg already set by canvas. Add gradient near spine.
    sr, sg, sb = config["spine_color"]
    for i in range(40):
        alpha = 60 - int(60 * (i / 40))
        x_pos = BLEED_PX + TRIM_W_PX - 1 - i
        if x_pos >= 0:
            br = int(config["back_bg"][0] * (1 - alpha / 255) + sr * (alpha / 255))
            bg = int(config["back_bg"][1] * (1 - alpha / 255) + sg * (alpha / 255))
            bb = int(config["back_bg"][2] * (1 - alpha / 255) + sb * (alpha / 255))
            draw.line([(x_pos, 0), (x_pos, TOTAL_H_PX)], fill=(br, bg, bb))

    # All back text inside safe zone
    back_margin_left = SAFE_PX      # 0.55" from left file edge
    back_margin_right = BLEED_PX + TRIM_W_PX - 80  # stop before spine
    back_text_width = back_margin_right - back_margin_left

    title_font = ImageFont.truetype(FONT_BOLD, 68)
    series_font = ImageFont.truetype(FONT_BOLD, 40)
    body_font = ImageFont.truetype(FONT_REG, 36)
    tagline_font = ImageFont.truetype(FONT_ITALIC, 30)
    age_font = ImageFont.truetype(FONT_BOLD, 34)
    small_font = ImageFont.truetype(FONT_REG, 26)

    text_color = config["back_text_color"]

    # Series name
    y = SAFE_PX + 30
    draw.text(
        (back_margin_left, y),
        "Adventures with Sam and Robo",
        font=series_font,
        fill=config["spine_color"],
    )
    y += 65

    # Book title
    draw.text(
        (back_margin_left, y),
        config["title"],
        font=title_font,
        fill=text_color,
    )
    y += 100

    # Divider
    draw.line(
        [(back_margin_left, y), (back_margin_right, y)],
        fill=config["spine_color"],
        width=3,
    )
    y += 35

    # Back cover copy
    y = draw_wrapped_text(
        draw, config["back_copy"],
        back_margin_left, y, back_text_width,
        body_font, text_color,
    )
    y += 25

    # Divider
    draw.line(
        [(back_margin_left, y), (back_margin_right, y)],
        fill=config["spine_color"],
        width=2,
    )
    y += 25

    # Age range
    draw.text(
        (back_margin_left, y),
        f"Ages 3-8  |  Grades PreK-2  |  Book {config['book_num']} of 5",
        font=age_font,
        fill=text_color,
    )
    y += 55

    # Tagline
    draw.text(
        (back_margin_left, y),
        '"Every word is a door. And every door is an adventure."',
        font=tagline_font,
        fill=config["spine_color"],
    )

    # Barcode area (bottom-right of back, inside safe zone)
    barcode_w = 400
    barcode_h = 260
    barcode_x = back_margin_right - barcode_w
    barcode_y = TOTAL_H_PX - SAFE_PX - barcode_h - 10
    draw.rectangle(
        [barcode_x, barcode_y,
         barcode_x + barcode_w, barcode_y + barcode_h],
        fill=(255, 255, 255),
        outline=(200, 200, 200),
        width=2,
    )
    draw.text(
        (barcode_x + 70, barcode_y + 95),
        "ISBN / BARCODE",
        font=small_font,
        fill=(180, 180, 180),
    )

    # Publisher name (bottom-left, inside safe zone)
    draw.text(
        (back_margin_left, TOTAL_H_PX - SAFE_PX - 50),
        "Everlight Kids",
        font=series_font,
        fill=config["spine_color"],
    )

    # ========================================
    # SAVE
    # ========================================
    config["cover_pdf"].parent.mkdir(parents=True, exist_ok=True)
    canvas.save(
        str(config["cover_pdf"]),
        "PDF",
        resolution=DPI,
        title=config["title"],
        author="Everlight Ventures Publishing",
    )

    size_mb = os.path.getsize(config["cover_pdf"]) / (1024 * 1024)
    print(f"  Saved: {config['cover_pdf']}")
    print(f"  Size: {size_mb:.1f} MB | {TOTAL_W_IN}\" x {TOTAL_H_IN}\" @ {DPI} DPI")
    print(f"  Safe zone: 0.55\" from outer edges (exceeds KDP 0.50\" min)")
    return True


def main():
    print("=" * 60)
    print("KDP FULL-WRAP COVER PDF GENERATOR (v3 SAFE ZONE)")
    print(f"Dimensions: {TOTAL_W_IN}\" x {TOTAL_H_IN}\" @ {DPI} DPI")
    print(f"Layout: back({TRIM_W}\") + spine({SPINE_W_IN:.3f}\") + front({TRIM_W}\")")
    print(f"Safe zone: 0.55\" (165px) from all outer edges")
    print(f"Pixels: {TOTAL_W_PX} x {TOTAL_H_PX}")
    print("=" * 60)

    results = []
    for book_id, config in BOOKS.items():
        ok = build_full_wrap(config)
        results.append((book_id, config["title"], ok))

    print("\n" + "=" * 60)
    for book_id, title, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  Book {book_id}: {title} -- {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
