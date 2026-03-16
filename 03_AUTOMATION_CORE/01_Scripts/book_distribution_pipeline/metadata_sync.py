#!/usr/bin/env python3
"""
metadata_sync.py -- Beyond the Veil platform metadata generator
Reads a single source-of-truth config and outputs formatted metadata
for KDP, ACX/Audible, IngramSpark, and social platforms.

Usage: python3 metadata_sync.py [--platform all|kdp|acx|ingram|social]
Output: ./metadata_output/<platform>_metadata.json or .txt
"""

import json
import os
import argparse
from datetime import datetime

# ============================================================
# SOURCE OF TRUTH -- Edit this block when anything changes
# ============================================================
BOOK = {
    "title": "Beyond the Veil",
    "subtitle": "",  # Add if applicable
    "author": "",    # TODO: Fill in author name
    "narrator": "",  # TODO: Fill in once contracted
    "series": "",    # If part of a series
    "series_number": 1,
    "language": "English",
    "description": "",  # TODO: Back-cover blurb (250-400 words for best conversion)
    "short_description": "",  # 100 words max for social/ads
    "keywords": [
        # TODO: Fill with 7 high-traffic keywords (use Publisher Rocket or Amazon autocomplete)
        # Example: "supernatural thriller", "mystery suspense", "dark secrets"
    ],
    "categories": {
        "kdp_primary": "",   # E.g., "Mystery, Thriller & Suspense > Thrillers > Supernatural"
        "kdp_secondary": "", # Second browse node
        "acx_genre": "Thriller & Suspense",  # ACX genre dropdown
    },
    "pricing": {
        "ebook_usd": 4.99,
        "audiobook_usd": 24.95,
        "paperback_usd": 14.99,
        "hardcover_usd": 24.99,
    },
    "isbn": {
        "ebook": "",      # KDP assigns free ASIN; use IngramSpark for ISBN
        "paperback": "",
        "hardcover": "",
        "audiobook": "",  # ACX assigns ASIN
    },
    "pages_estimated": 0,   # TODO: fill
    "word_count": 0,        # TODO: fill
    "audio_hours_estimated": 0,  # word_count / 9000
    "publication_date": "",  # YYYY-MM-DD; leave blank until ready
    "copyright_year": datetime.now().year,
    "publisher": "Everlight Ventures Publishing",
    "cover_image_path": "../01_BUSINESSES/Publishing/Beyond_The_Veil/06_Cover_Art/cover_final.jpg",
}

# ============================================================

def validate_book():
    """Check for empty required fields and warn."""
    required = ["title", "author", "description"]
    warnings = []
    for field in required:
        if not BOOK.get(field):
            warnings.append(f"WARNING: '{field}' is empty")
    if not BOOK["keywords"]:
        warnings.append("WARNING: No keywords defined -- discovery will suffer")
    if not BOOK["categories"]["kdp_primary"]:
        warnings.append("WARNING: KDP primary category not set")
    return warnings


def build_kdp_metadata():
    """Amazon KDP ebook + paperback metadata."""
    return {
        "platform": "Amazon KDP",
        "title": BOOK["title"],
        "subtitle": BOOK.get("subtitle", ""),
        "author": BOOK["author"],
        "language": BOOK["language"],
        "description_html": f"<p>{BOOK['description']}</p>",
        "keywords": BOOK["keywords"][:7],  # KDP max 7
        "primary_category": BOOK["categories"]["kdp_primary"],
        "secondary_category": BOOK["categories"]["kdp_secondary"],
        "pricing": {
            "ebook_usd": BOOK["pricing"]["ebook_usd"],
            "paperback_usd": BOOK["pricing"]["paperback_usd"],
        },
        "enrollment": "KDP Select (Kindle Unlimited) -- 90-day exclusive",
        "notes": [
            "70% royalty requires price $2.99-$9.99",
            "Enable X-Ray and Enhanced Typesetting for quality badge",
            "Submit to BookBub 2 weeks before launch",
        ]
    }


def build_acx_metadata():
    """ACX/Audible audiobook metadata."""
    audio_hours = BOOK["word_count"] / 9000 if BOOK["word_count"] else BOOK["audio_hours_estimated"]
    return {
        "platform": "ACX / Audible",
        "title": BOOK["title"],
        "author": BOOK["author"],
        "narrator": BOOK["narrator"],
        "genre": BOOK["categories"]["acx_genre"],
        "language": BOOK["language"],
        "description": BOOK["description"][:4000],  # ACX limit
        "keywords": " ".join(BOOK["keywords"][:5]),
        "estimated_audio_hours": round(audio_hours, 1),
        "list_price_usd": BOOK["pricing"]["audiobook_usd"],
        "royalty_rate_exclusive": "40% of list price (Audible exclusive 90 days)",
        "royalty_rate_nonexclusive": "25% of list price",
        "narrator_agreement": "See 03_Contracted/ folder",
        "technical_requirements": {
            "format": "WAV 44.1kHz 16-bit mono",
            "rms": "-23 to -18 dBFS",
            "noise_floor": "< -60 dBFS",
            "peak": "< -3 dBFS",
        }
    }


def build_ingram_metadata():
    """IngramSpark print + wide distribution metadata."""
    return {
        "platform": "IngramSpark",
        "title": BOOK["title"],
        "author": BOOK["author"],
        "publisher": BOOK["publisher"],
        "isbn_paperback": BOOK["isbn"]["paperback"],
        "isbn_hardcover": BOOK["isbn"]["hardcover"],
        "language": BOOK["language"],
        "bisac_code": "",  # TODO: Add BISAC code (e.g., FIC031010 for Thrillers)
        "description": BOOK["description"][:10000],
        "pricing": {
            "paperback_usd": BOOK["pricing"]["paperback_usd"],
            "hardcover_usd": BOOK["pricing"]["hardcover_usd"],
        },
        "distribution_channels": ["Amazon", "Barnes & Noble", "Baker & Taylor", "Libraries"],
        "setup_fee": "$49 per title format (one-time)",
        "notes": [
            "Print-ready PDF must be press-quality (300 DPI, CMYK)",
            "Cover must include spine width calculated by page count",
            "Allow 6-8 weeks for worldwide distribution activation",
        ]
    }


def build_social_metadata():
    """Social media bio/caption templates."""
    return {
        "platform": "Social (TikTok / Instagram)",
        "title_handle": BOOK["title"].replace(" ", ""),
        "hashtags": [
            "#BeyondTheVeil",
            "#NewRelease",
            "#AudioBook",
            "#Thriller",
            "#Suspense",
            "#BookTok",
            "#BookstagramFeature",
        ],
        "caption_template_launch": (
            f"New audiobook just dropped. \"{BOOK['title']}\" -- "
            "the kind of story you listen to alone, in the dark. "
            "Link in bio. #BeyondTheVeil #AudioBook #BookTok"
        ),
        "caption_template_clip": (
            "One chapter. One voice. You'll understand why everyone's talking. "
            "#BeyondTheVeil"
        ),
        "bio_blurb": BOOK["short_description"] or BOOK["description"][:150],
        "link_in_bio_priority": ["Audible", "Amazon KDP", "Author website"],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate platform metadata for Beyond the Veil")
    parser.add_argument(
        "--platform",
        default="all",
        choices=["all", "kdp", "acx", "ingram", "social"],
        help="Which platform to generate metadata for"
    )
    args = parser.parse_args()

    output_dir = os.path.join(
        os.path.dirname(__file__),
        "../../../01_BUSINESSES/Publishing/Beyond_The_Veil/08_Platform_Metadata"
    )
    os.makedirs(output_dir, exist_ok=True)

    warnings = validate_book()
    if warnings:
        print("\n".join(warnings))
        print("")

    platforms = {
        "kdp": build_kdp_metadata,
        "acx": build_acx_metadata,
        "ingram": build_ingram_metadata,
        "social": build_social_metadata,
    }

    to_run = platforms.keys() if args.platform == "all" else [args.platform]

    for name in to_run:
        data = platforms[name]()
        outfile = os.path.join(output_dir, f"{name}_metadata.json")
        with open(outfile, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Written: {outfile}")

    print("\nNext: Fill in TODO fields in BOOK config at top of this file, then re-run.")


if __name__ == "__main__":
    main()
