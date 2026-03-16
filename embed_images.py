"""Embed images as base64 into reader HTML files for Android compatibility."""
import base64
import re
import os
from PIL import Image
from io import BytesIO

BOOKS = [
    {
        "html": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/Book1/Sams_First_Superpower_reader.html",
        "img_dir": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/Book1/images",
    },
    {
        "html": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/Book 2/Sams_Second_Superpower_reader.html",
        "img_dir": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/Book 2/images",
    },
    {
        "html": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/book_4/Sams_Fourth_Superpower_reader.html",
        "img_dir": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/book_4/images",
    },
    {
        "html": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/book_5/Sams_Fifth_Superpower_reader.html",
        "img_dir": "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM/book_5/images",
    },
]

MAX_WIDTH = 800
JPEG_QUALITY = 72


def compress_and_encode(img_path):
    """Load image, resize to max width, compress, return base64 string."""
    img = Image.open(img_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    if w > MAX_WIDTH:
        ratio = MAX_WIDTH / w
        img = img.resize((MAX_WIDTH, int(h * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def process_book(book):
    html_path = book["html"]
    img_dir = book["img_dir"]
    book_name = os.path.basename(os.path.dirname(html_path))

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(r'<img\s+src="images/([^"]+)"')
    matches = pattern.findall(html)
    print(f"\n[{book_name}] Found {len(matches)} image references")

    replaced = 0
    for filename in matches:
        img_path = os.path.join(img_dir, filename)
        if not os.path.exists(img_path):
            print(f"  WARNING: {filename} not found at {img_path}")
            continue
        b64_data = compress_and_encode(img_path)
        old_src = f'src="images/{filename}"'
        new_src = f'src="{b64_data}"'
        html = html.replace(old_src, new_src, 1)
        size_kb = len(b64_data) // 1024
        replaced += 1
        print(f"  Embedded: {filename} ({size_kb} KB base64)")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    final_kb = os.path.getsize(html_path) // 1024
    print(f"  [{book_name}] Done: {replaced}/{len(matches)} images embedded, file size: {final_kb} KB")


if __name__ == "__main__":
    for book in BOOKS:
        process_book(book)
    print("\nAll books processed. Reader HTML files are now self-contained.")
