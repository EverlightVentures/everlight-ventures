#!/usr/bin/env python3
"""
generate_trailer_samples.py - Everlight Hollywood Trailer Audio Preview Generator
Hive Mind: hive_83877943 | 2026-03-10

Generates 30-second cinematic audio previews for each book.

Rules (per user spec):
  - NEVER narrate title, prologue, or table of contents
  - Target the most tension-filled passage (peak anticipation moment)
  - ~250-300 words at cinematic pace (~30 seconds spoken)
  - ElevenLabs with dramatic voice settings (high style, low stability)
  - Output: book audiobook/ dir as trailer_sample.mp3

Usage:
    python generate_trailer_samples.py             # all books
    python generate_trailer_samples.py --book btv  # single book
    python generate_trailer_samples.py --dry-run   # list without generating
"""

import os
import sys
import logging
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(WORKSPACE / "06_DEVELOPMENT"))

from speech_service import generate_trailer_sample, get_usage_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("trailer_gen")

BASE_LIT = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Everlight_Literature/Ebook_Sells"

# ---------------------------------------------------------------------------
# Trailer scripts
# Curated peak-tension passages. NOT title / prologue / TOC.
# ~250 words each, written for cinematic spoken delivery.
# ---------------------------------------------------------------------------

TRAILERS = {
    "sam_1": {
        "title": "Sam's First Superpower",
        "genre": "kids",
        "output": BASE_LIT / "Adventures_Series/ADVENTURES_WITH_SAM/Book1/audiobook/trailer_sample.mp3",
        "script": (
            "Sam found the book under the old oak tree on a Tuesday. "
            "He almost walked right past it. Almost.\n\n"
            "Robo's eyes lit up the moment Sam touched the cover. "
            "Not the usual soft blue glow. This was bright. Urgent. Like a warning.\n\n"
            "The word inside the book glowed. One single word Sam had never seen before. "
            "And then he could read it. "
            "Not slowly, sounding it out the way his teacher showed him. "
            "Instantly. Completely. As if he had always known it.\n\n"
            "Something had unlocked inside him.\n\n"
            "Robo beeped twice. The code that meant: run. "
            "Sam didn't ask why. He ran.\n\n"
            "Every child has a power sleeping inside them, "
            "waiting for the right moment to wake up. "
            "Sam's moment was now. "
            "And what happened next would change everything, "
            "for Sam, for Robo, and for every kid who ever felt "
            "like they weren't quite enough.\n\n"
            "From Everlight Kids. "
            "Sam's First Superpower. "
            "The adventure begins."
        ),
    },
    "sam_2": {
        "title": "Sam's Second Superpower",
        "genre": "kids",
        "output": BASE_LIT / "Adventures_Series/ADVENTURES_WITH_SAM/Book 2/audiobook/trailer_sample.mp3",
        "script": (
            "Sam thought he knew what he was capable of. He was wrong.\n\n"
            "Robo had gone quiet. "
            "Not the good kind of quiet. "
            "The kind that means something is wrong "
            "and the robot is trying to protect you from knowing it.\n\n"
            "Three nights in a row, Sam woke up knowing things he hadn't learned. "
            "Numbers that solved themselves. "
            "Words in languages he had never studied. "
            "A map of a place he had never been, "
            "drawn perfectly in his own handwriting.\n\n"
            "Mom thought he was dreaming. "
            "Dad thought he was showing off. "
            "Robo blinked his amber warning light and said nothing at all.\n\n"
            "Then the messages started appearing. "
            "On his desk. On the mirror. On the inside of his own sneakers. "
            "All the same two words: Find it.\n\n"
            "What Sam didn't know was that his second superpower "
            "didn't come from the book. "
            "It came from inside him. "
            "And it had been waiting his entire life for this exact moment.\n\n"
            "From Everlight Kids. "
            "Sam's Second Superpower. "
            "Bigger than the first."
        ),
    },
    "btv": {
        "title": "Beyond the Veil",
        "genre": "thriller",
        "output": BASE_LIT / "BEYOND_THE_VEIL_HaileyPink_Book1/audiobook/trailer_sample.mp3",
        "script": (
            "She left her body at 2:47 in the morning.\n\n"
            "Deputy Hailey Pink had done it hundreds of times before. "
            "Slipped free of sleep, floated above the town, "
            "watched the dark streets from somewhere safe and unreachable.\n\n"
            "But tonight, something was different.\n\n"
            "Tonight, there was something else out there. "
            "Waiting in the space between worlds. "
            "And it had learned her name.\n\n"
            "By morning, the first resident had fallen into a coma. "
            "No cause. No fever. No explanation. "
            "Just gone. Eyes open. Breathing. But completely unreachable.\n\n"
            "Hailey knew it wasn't a virus. "
            "She knew it wasn't drugs. "
            "She had seen what was hunting her town, "
            "and it wasn't from this world.\n\n"
            "The real battle wouldn't be fought in the streets. "
            "It would be fought inside the mind. "
            "Inside the dark. "
            "Inside a place where Hailey Pink was either "
            "the only person who could stop it, "
            "or its next victim.\n\n"
            "Beyond the Veil. "
            "A quantum western thriller. "
            "From Everlight Ventures Publishing. "
            "Coming 2026."
        ),
    },
}


def generate_all(dry_run: bool = False, book_filter: str | None = None):
    books = TRAILERS if not book_filter else {
        k: v for k, v in TRAILERS.items() if k == book_filter
    }

    if not books:
        log.error(f"No matching book: '{book_filter}'. Options: {list(TRAILERS.keys())}")
        sys.exit(1)

    log.info(f"Trailer generator - {len(books)} book(s) | dry_run={dry_run}")

    if not dry_run:
        report = get_usage_report()
        el_remaining = report["elevenlabs"]["remaining"]
        total_chars  = sum(len(b["script"]) for b in books.values())
        log.info(
            f"ElevenLabs remaining: {el_remaining:,} chars | "
            f"needed: {total_chars:,} chars"
        )
        if total_chars > el_remaining:
            log.warning("Quota low - will fall back to MiniMax/OpenAI as needed")

    results = []
    for key, config in books.items():
        log.info(f"\n--- {config['title']} [{key}] ---")
        if dry_run:
            print(f"  [DRY RUN] Would generate: {config['output']}")
            print(f"  Script ({len(config['script'])} chars): "
                  + config["script"][:100] + "...")
            results.append({"book": config["title"], "status": "dry_run"})
            continue

        try:
            output_path = generate_trailer_sample(
                text=config["script"],
                book_id=key,
                output_path=config["output"],
                genre=config["genre"],
            )
            results.append({"book": config["title"], "status": "ok",
                            "path": str(output_path)})
        except Exception as e:
            log.error(f"FAILED {config['title']}: {e}")
            results.append({"book": config["title"], "status": "failed",
                            "error": str(e)})

    print("\n=== RESULTS ===")
    for r in results:
        if r["status"] == "ok":
            print(f"  OK   {r['book']} -> {r['path']}")
        elif r["status"] == "dry_run":
            print(f"  DRY  {r['book']}")
        else:
            print(f"  FAIL {r['book']}: {r.get('error')}")


if __name__ == "__main__":
    dry_run     = "--dry-run" in sys.argv
    book_filter = None
    if "--book" in sys.argv:
        idx = sys.argv.index("--book")
        if idx + 1 < len(sys.argv):
            book_filter = sys.argv[idx + 1]

    generate_all(dry_run=dry_run, book_filter=book_filter)
