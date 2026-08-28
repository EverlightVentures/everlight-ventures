"""Embed images as base64 into reader HTML files for Android compatibility."""
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from shared.publishing.book_config import BOOKS as BOOK_REGISTRY
from shared.publishing.image_utils import compress_and_encode

# Build BOOKS list from central registry (previously duplicated inline)
BOOKS = []
for _bid in [1, 2, 4, 5]:
    _b = BOOK_REGISTRY[_bid]
    _stem = _b["title"].replace("'", "").replace(" ", "_")
    BOOKS.append({
        "html": str(_b["dir"] / f"{_stem}_reader.html"),
        "img_dir": str(_b["img_dir"]),
    })

MAX_WIDTH = 800
JPEG_QUALITY = 72

# compress_and_encode is now imported from shared.publishing.image_utils


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
