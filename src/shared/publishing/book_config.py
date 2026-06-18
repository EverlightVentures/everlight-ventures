"""
Central book registry for the Adventures with Sam and Robo series.

All build scripts (build_books, build_audiobooks, build_cover_pdfs,
build_ebook_covers, generate_book_images, generate_covers, embed_images)
should import book metadata from here instead of duplicating it.
"""

from pathlib import Path

BASE_DIR = Path(
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/"
    "Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM"
)

SERIES_AUTHOR = "Everlight Kids"
SERIES_PUBLISHER = "Everlight Ventures"
SERIES_NAME = "Adventures with Sam and Robo"
TOTAL_BOOKS = 5

BOOKS = {
    1: {
        "title": "Sam's First Superpower",
        "subtitle": "Adventures with Sam and Robo -- Book 1",
        "dir": BASE_DIR / "Book1",
        "manuscript": BASE_DIR / "Book1/Sams_First_Superpower_MASTER.md",
        "manuscript_type": "md",
        "img_dir": BASE_DIR / "Book1/images",
        "cover_jpg": BASE_DIR / "Book1/images/1_cover.jpg",
        "prefix": "1",
        "scenes": 12,
        "spine_color": (218, 165, 32),
        "front_bg": (25, 35, 55),
        "back_bg": (255, 248, 220),
        "back_text_color": (60, 40, 10),
        "accent": (218, 165, 32),
        "ebook_bg_top": (30, 60, 100),
        "ebook_bg_bottom": (20, 45, 75),
    },
    2: {
        "title": "Sam's Second Superpower",
        "subtitle": "Adventures with Sam and Robo -- Book 2",
        "dir": BASE_DIR / "Book 2",
        "manuscript": BASE_DIR / "Book 2/Sams_Second_Superpower_MASTER.md",
        "manuscript_type": "md",
        "img_dir": BASE_DIR / "Book 2/images",
        "cover_jpg": BASE_DIR / "Book 2/images/2_cover.jpg",
        "prefix": "2",
        "scenes": 11,
        "spine_color": (30, 100, 200),
        "front_bg": (10, 25, 60),
        "back_bg": (230, 240, 255),
        "back_text_color": (15, 30, 60),
        "accent": (80, 180, 255),
        "ebook_bg_top": (15, 40, 90),
        "ebook_bg_bottom": (10, 30, 70),
    },
    3: {
        "title": "Sam's Third Superpower",
        "subtitle": "Adventures with Sam and Robo -- Book 3",
        "dir": BASE_DIR / "book_3",
        "manuscript": BASE_DIR / "book_3/Sams_Third_Superpower.docx",
        "manuscript_type": "docx",
        "img_dir": BASE_DIR / "book_3/images",
        "cover_jpg": BASE_DIR / "book_3/images/3_cover.jpg",
        "prefix": "3",
        "scenes": 12,
        "spine_color": (100, 40, 150),
        "front_bg": (30, 10, 50),
        "back_bg": (245, 235, 255),
        "back_text_color": (35, 15, 55),
        "accent": (180, 120, 255),
        "ebook_bg_top": (50, 20, 80),
        "ebook_bg_bottom": (35, 10, 60),
    },
    4: {
        "title": "Sam's Fourth Superpower",
        "subtitle": "Adventures with Sam and Robo -- Book 4",
        "dir": BASE_DIR / "book_4",
        "manuscript": BASE_DIR / "book_4/manuscript/Sams_Fourth_Superpower_MASTER.md",
        "manuscript_type": "md",
        "img_dir": BASE_DIR / "book_4/images",
        "cover_jpg": BASE_DIR / "book_4/images/4_cover.jpg",
        "prefix": "4",
        "scenes": 12,
        "spine_color": (34, 139, 34),
        "front_bg": (10, 40, 15),
        "back_bg": (230, 250, 230),
        "back_text_color": (15, 45, 15),
        "accent": (80, 200, 100),
        "ebook_bg_top": (15, 60, 30),
        "ebook_bg_bottom": (10, 45, 20),
    },
    5: {
        "title": "Sam's Fifth Superpower",
        "subtitle": "Adventures with Sam and Robo -- Book 5",
        "dir": BASE_DIR / "book_5",
        "manuscript": BASE_DIR / "book_5/manuscript/Sams_Fifth_Superpower_MASTER.md",
        "manuscript_type": "md",
        "img_dir": BASE_DIR / "book_5/images",
        "cover_jpg": BASE_DIR / "book_5/images/5_cover.jpg",
        "prefix": "5",
        "scenes": 12,
        "spine_color": (255, 140, 0),
        "front_bg": (50, 25, 5),
        "back_bg": (255, 245, 230),
        "back_text_color": (60, 30, 5),
        "accent": (255, 180, 60),
        "ebook_bg_top": (90, 45, 10),
        "ebook_bg_bottom": (70, 35, 8),
    },
}


def get_book(book_id: int) -> dict:
    """Retrieve book config by ID. Raises KeyError if not found."""
    return BOOKS[book_id]


def get_output_paths(book_id: int) -> dict:
    """Derive standard output paths for a given book."""
    b = BOOKS[book_id]
    stem = b["title"].replace("'", "").replace(" ", "_")
    d = b["dir"]
    return {
        "out_docx": d / f"{stem}_KDP.docx",
        "out_epub": d / f"{stem}.epub",
        "reader_html": d / f"{stem}_reader.html",
        "audio_dir": d / "audiobook",
        "cover_print_pdf": b["img_dir"] / f"{b['prefix']}_cover_print.pdf",
        "cover_ebook_jpg": b["img_dir"] / f"{b['prefix']}_cover_ebook.jpg",
    }
