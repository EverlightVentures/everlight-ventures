"""
Build ACX-compliant audiobooks for Sam's Superpower Series (Books 1-5).
Uses OpenAI TTS API (tts-1-hd, voice: nova) with ffmpeg post-processing.

ACX Technical Requirements:
  - MP3, 192 kbps CBR, 44.1 kHz, mono
  - Peak below -3 dB, RMS between -23 and -18 dB, noise floor below -60 dB
  - 0.5-1s room tone at head/tail of each file
  - Opening credits, chapter files, closing credits, retail sample
"""
import os
import re
import time
import requests
from pathlib import Path
from io import BytesIO
from pydub import AudioSegment
from docx import Document as DocxDocument

# ============================================================
# CONFIG
# ============================================================
API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM")

TTS_MODEL = "tts-1-hd"
TTS_VOICE = "fable"  # Expressive storytelling voice -- warm, captivating, soothing for kids
MAX_CHARS = 4000  # OpenAI TTS limit is 4096, leave margin
AUTHOR = "Everlight Kids"
NARRATOR = "Fable"  # Virtual voice name for credits
PUBLISHER = "Everlight Ventures"
COPYRIGHT_YEAR = "2026"

BOOKS = [
    {
        "id": 1,
        "title": "Sam's First Superpower",
        "subtitle": "Adventures with Sam and Robo, Book 1",
        "source": BASE / "Book1/Sams_First_Superpower_MASTER.md",
        "source_type": "md",
        "audio_dir": BASE / "Book1/audiobook",
    },
    {
        "id": 2,
        "title": "Sam's Second Superpower",
        "subtitle": "Adventures with Sam and Robo, Book 2",
        "source": BASE / "Book 2/Sams_Second_Superpower_MASTER.md",
        "source_type": "md",
        "audio_dir": BASE / "Book 2/audiobook",
    },
    {
        "id": 3,
        "title": "Sam's Third Superpower",
        "subtitle": "Adventures with Sam and Robo, Book 3",
        "source": BASE / "book_3/Sams_Third_Superpower.docx",
        "source_type": "docx",
        "audio_dir": BASE / "book_3/audiobook",
    },
    {
        "id": 4,
        "title": "Sam's Fourth Superpower",
        "subtitle": "Adventures with Sam and Robo, Book 4",
        "source": BASE / "book_4/manuscript/Sams_Fourth_Superpower_MASTER.md",
        "source_type": "md",
        "audio_dir": BASE / "book_4/audiobook",
    },
    {
        "id": 5,
        "title": "Sam's Fifth Superpower",
        "subtitle": "Adventures with Sam and Robo, Book 5",
        "source": BASE / "book_5/manuscript/Sams_Fifth_Superpower_MASTER.md",
        "source_type": "md",
        "audio_dir": BASE / "book_5/audiobook",
    },
]


# ============================================================
# TEXT EXTRACTION
# ============================================================
def extract_chapters_from_md(md_path):
    """Parse MASTER.md into chapters of narration-ready text."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip markdown formatting for narration
    def clean_for_narration(text):
        # Remove image references
        text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
        # Remove horizontal rules
        text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
        # Remove markdown headers (keep the text)
        text = re.sub(r"^#{1,4}\s+", "", text, flags=re.MULTILINE)
        # Convert bold to plain
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        # Convert italic to plain
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        # Remove metadata lines
        skip_patterns = [
            r"^\*\*Document Status:.*$",
            r"^\*\*Date:.*$",
            r"^\*\*Format:.*$",
            r"^\*\*Page Layout:.*$",
            r"^\*\*Phonics Focus:.*$",
            r"^\*\*Core Value:.*$",
            r"^\*\*CASEL.*$",
            r"^\*\*CCSS.*$",
            r"^\*\*Superpower Unlocked:.*$",
            r"^\*\*Target Age:.*$",
            r"^\*\*Series Position:.*$",
            r"^End of Master Manuscript.*$",
            r"^Next steps:.*$",
            r"^\> \[ASSISTANT NOTE.*$",
        ]
        for pat in skip_patterns:
            text = re.sub(pat, "", text, flags=re.MULTILINE)
        # Clean up multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # Split into chapters
    # Look for "CHAPTER" headers or "## CHAPTER" or "SERIES RECAP" or "BACK MATTER"
    chapter_pattern = re.compile(
        r"(?:^|\n)(?:#{1,3}\s+)?(CHAPTER \d+[:\s].*?|SERIES RECAP.*?|BACK MATTER.*?|THE LEARNING CORNER.*?|THE VALUES MOMENT.*?)(?:\n|$)",
        re.IGNORECASE
    )

    sections = []
    matches = list(chapter_pattern.finditer(content))

    if not matches:
        # Fallback: treat entire content as one chapter
        sections.append(("Full Story", clean_for_narration(content)))
    else:
        # Add Series Recap as intro if present before first chapter
        first_match_pos = matches[0].start()
        intro = content[:first_match_pos].strip()
        if intro and len(intro) > 100:
            cleaned_intro = clean_for_narration(intro)
            if cleaned_intro:
                sections.append(("Introduction", cleaned_intro))

        for i, m in enumerate(matches):
            title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_text = content[start:end]
            cleaned = clean_for_narration(section_text)

            # Skip very short sections (metadata only)
            if len(cleaned) < 50:
                continue

            # Convert Interactive Moments for narration
            cleaned = re.sub(
                r"Interactive Moment:\s*",
                "Here's an interactive moment for you! ",
                cleaned
            )
            # Convert Q&A for narration
            cleaned = re.sub(r"Question:\s*", "Here's a question to think about: ", cleaned)
            cleaned = re.sub(r"Answer:\s*", "The answer is: ", cleaned)

            sections.append((title, cleaned))

    return sections


def extract_chapters_from_docx(docx_path):
    """Parse DOCX into chapters of narration-ready text."""
    doc = DocxDocument(str(docx_path))
    full_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)

    content = "\n\n".join(full_text)

    # Split by "Chapter N:" pattern
    chapter_pattern = re.compile(r"(Chapter \d+[:\s].*?)(?=\n|$)", re.IGNORECASE)
    matches = list(chapter_pattern.finditer(content))

    sections = []
    if not matches:
        sections.append(("Full Story", content))
    else:
        # Intro before first chapter
        intro = content[:matches[0].start()].strip()
        if intro and len(intro) > 50:
            sections.append(("Introduction", intro))

        for i, m in enumerate(matches):
            title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_text = content[start:end].strip()

            # Clean for narration
            section_text = re.sub(
                r"Interactive Moment:\s*",
                "Here's an interactive moment for you! ",
                section_text
            )
            section_text = re.sub(r"Question:\s*", "Here's a question to think about: ", section_text)
            section_text = re.sub(r"Answer:\s*", "The answer is: ", section_text)

            if len(section_text) > 30:
                sections.append((title, section_text))

    return sections


# ============================================================
# TTS GENERATION
# ============================================================
def tts_generate(text, output_path):
    """Call OpenAI TTS API and save MP3."""
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": TTS_MODEL,
        "input": text,
        "voice": TTS_VOICE,
        "response_format": "mp3",
        "speed": 0.95,  # Slightly slower for children's content
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"    TTS Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"    Details: {e.response.text[:300]}")
        return False


def generate_audio_for_text(text, output_path):
    """Split long text into chunks, generate TTS for each, concatenate."""
    # Split into chunks respecting sentence boundaries
    chunks = split_text_into_chunks(text, MAX_CHARS)

    if len(chunks) == 1:
        return tts_generate(chunks[0], output_path)

    # Generate each chunk
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_path = str(output_path).replace(".mp3", f"_chunk{i}.mp3")
        print(f"      Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        if tts_generate(chunk, chunk_path):
            chunk_files.append(chunk_path)
            time.sleep(0.5)
        else:
            print(f"      Failed chunk {i+1}")
            # Clean up
            for cf in chunk_files:
                if os.path.exists(cf):
                    os.remove(cf)
            return False

    # Concatenate chunks
    combined = AudioSegment.empty()
    for cf in chunk_files:
        segment = AudioSegment.from_mp3(cf)
        combined += segment
        os.remove(cf)  # Clean up chunk file

    combined.export(str(output_path), format="mp3", bitrate="192k")
    return True


def split_text_into_chunks(text, max_chars):
    """Split text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ""

    # Split by sentences (period, !, ?)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = current + " " + sentence if current else sentence
        else:
            if current:
                chunks.append(current.strip())
            # Handle single sentences longer than max
            if len(sentence) > max_chars:
                # Split by paragraph or comma
                parts = sentence.split("\n\n")
                for part in parts:
                    if len(part) <= max_chars:
                        current = part
                    else:
                        chunks.append(part[:max_chars])
                        current = part[max_chars:]
            else:
                current = sentence

    if current:
        chunks.append(current.strip())

    return [c for c in chunks if c.strip()]


# ============================================================
# ACX POST-PROCESSING
# ============================================================
def acx_master(input_path, output_path):
    """
    Post-process audio to ACX specs using pydub:
    - 44.1 kHz, mono
    - 192 kbps CBR MP3
    - Add 0.75s silence at head/tail
    - Normalize to target RMS (-20 dB)
    """
    audio = AudioSegment.from_mp3(str(input_path))

    # Convert to mono, 44.1 kHz
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(44100)

    # Add room tone (silence) at head and tail
    silence = AudioSegment.silent(duration=750)  # 0.75 seconds
    audio = silence + audio + silence

    # Normalize: target RMS of -20 dB (ACX range is -18 to -23)
    target_rms = -20.0
    current_rms = audio.rms
    if current_rms > 0:
        current_db = audio.dBFS
        change_db = target_rms - current_db
        audio = audio.apply_gain(change_db)

    # Export as 192 kbps CBR MP3
    audio.export(
        str(output_path),
        format="mp3",
        bitrate="192k",
        parameters=["-ar", "44100", "-ac", "1"],
    )

    # Clean up raw file
    if str(input_path) != str(output_path) and os.path.exists(str(input_path)):
        os.remove(str(input_path))


# ============================================================
# BOOK PROCESSING
# ============================================================
def build_audiobook(book):
    """Build complete ACX-ready audiobook for one book."""
    book_id = book["id"]
    title = book["title"]
    audio_dir = book["audio_dir"]
    audio_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  AUDIOBOOK {book_id}: {title}")
    print(f"{'='*60}")

    # Check if already complete
    final_check = audio_dir / f"book{book_id}_complete.mp3"
    if final_check.exists():
        print(f"  Already complete! Skipping. Delete {final_check} to rebuild.")
        return True

    # 1. Extract chapters
    print(f"\n  [1] Extracting chapters...")
    if book["source_type"] == "md":
        chapters = extract_chapters_from_md(book["source"])
    else:
        chapters = extract_chapters_from_docx(book["source"])

    print(f"  Found {len(chapters)} sections")
    for i, (ch_title, ch_text) in enumerate(chapters):
        print(f"    {i+1}. {ch_title} ({len(ch_text)} chars)")

    # 2. Generate opening credits
    print(f"\n  [2] Generating opening credits...")
    opening_text = (
        f"{title}. {book['subtitle']}. "
        f"Written by {AUTHOR}. Narrated by {NARRATOR}. "
        f"Published by {PUBLISHER}."
    )
    raw_opening = audio_dir / "raw_opening.mp3"
    opening_file = audio_dir / f"00_opening_credits.mp3"
    if not opening_file.exists():
        if tts_generate(opening_text, str(raw_opening)):
            acx_master(raw_opening, opening_file)
            print(f"    Created: {opening_file.name}")
        else:
            print(f"    FAILED opening credits")
    else:
        print(f"    Already exists, skipping")

    # 3. Generate chapter audio
    print(f"\n  [3] Generating chapter audio...")
    chapter_files = [opening_file]

    for i, (ch_title, ch_text) in enumerate(chapters):
        ch_num = i + 1
        raw_path = audio_dir / f"raw_ch{ch_num:02d}.mp3"
        final_path = audio_dir / f"{ch_num:02d}_{ch_title.replace(' ', '_').replace(':', '').replace('/', '_')[:40]}.mp3"

        if final_path.exists():
            print(f"    Chapter {ch_num} already exists, skipping")
            chapter_files.append(final_path)
            continue

        print(f"    Chapter {ch_num}: {ch_title}")

        # Add chapter announcement
        narration_text = f"{ch_title}.\n\n{ch_text}"

        if generate_audio_for_text(narration_text, str(raw_path)):
            acx_master(raw_path, final_path)
            size_kb = os.path.getsize(str(final_path)) // 1024
            duration_s = len(AudioSegment.from_mp3(str(final_path))) / 1000
            print(f"    Created: {final_path.name} ({size_kb} KB, {duration_s:.0f}s)")
            chapter_files.append(final_path)
            time.sleep(0.5)
        else:
            print(f"    FAILED chapter {ch_num}")

    # 4. Generate closing credits
    print(f"\n  [4] Generating closing credits...")
    closing_text = (
        f"This has been {title}, {book['subtitle']}. "
        f"Written by {AUTHOR}. Narrated by {NARRATOR}. "
        f"Copyright {COPYRIGHT_YEAR} {PUBLISHER}. All rights reserved. "
        f"Thank you for listening! If you enjoyed this story, please leave a review "
        f"and check out the other books in the Adventures with Sam and Robo series."
    )
    raw_closing = audio_dir / "raw_closing.mp3"
    closing_file = audio_dir / f"99_closing_credits.mp3"
    if not closing_file.exists():
        if tts_generate(closing_text, str(raw_closing)):
            acx_master(raw_closing, closing_file)
            print(f"    Created: {closing_file.name}")
        else:
            print(f"    FAILED closing credits")
    else:
        print(f"    Already exists, skipping")

    chapter_files.append(closing_file)

    # 5. Build complete audiobook (single file)
    print(f"\n  [5] Building complete audiobook...")
    combined = AudioSegment.empty()
    for cf in chapter_files:
        if cf.exists():
            segment = AudioSegment.from_mp3(str(cf))
            combined += segment
            # Add 1.5s pause between sections
            combined += AudioSegment.silent(duration=1500)

    combined.export(
        str(final_check),
        format="mp3",
        bitrate="192k",
        parameters=["-ar", "44100", "-ac", "1"],
    )
    total_duration = len(combined) / 1000
    total_mb = os.path.getsize(str(final_check)) / (1024 * 1024)
    print(f"    Complete: {final_check.name} ({total_mb:.1f} MB, {total_duration/60:.1f} min)")

    # 6. Generate retail sample (first 3-5 minutes)
    print(f"\n  [6] Generating retail sample...")
    sample_file = audio_dir / f"book{book_id}_sample.mp3"
    if not sample_file.exists():
        sample_duration_ms = min(300000, len(combined))  # 5 min max
        sample = combined[:sample_duration_ms]
        # Fade out last 3 seconds
        sample = sample.fade_out(3000)
        sample.export(
            str(sample_file),
            format="mp3",
            bitrate="192k",
            parameters=["-ar", "44100", "-ac", "1"],
        )
        sample_mb = os.path.getsize(str(sample_file)) / (1024 * 1024)
        print(f"    Sample: {sample_file.name} ({sample_mb:.1f} MB, {sample_duration_ms/60000:.1f} min)")
    else:
        print(f"    Already exists, skipping")

    print(f"\n  AUDIOBOOK {book_id} COMPLETE!")
    return True


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import sys

    # Allow processing specific books: python build_audiobooks.py 5
    # Or all books: python build_audiobooks.py
    if len(sys.argv) > 1:
        book_ids = [int(x) for x in sys.argv[1:]]
        books_to_process = [b for b in BOOKS if b["id"] in book_ids]
    else:
        books_to_process = BOOKS

    print(f"Building audiobooks for {len(books_to_process)} books...")
    print(f"TTS: OpenAI {TTS_MODEL}, voice: {TTS_VOICE}")
    print(f"ACX specs: 192kbps CBR, 44.1kHz, mono")

    for book in books_to_process:
        build_audiobook(book)

    print(f"\n{'='*60}")
    print("  ALL AUDIOBOOKS COMPLETE!")
    print(f"{'='*60}")
    print("\nOutput directories:")
    for book in books_to_process:
        audio_dir = book["audio_dir"]
        if audio_dir.exists():
            files = list(audio_dir.glob("*.mp3"))
            total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
            print(f"  Book {book['id']}: {audio_dir} ({len(files)} files, {total_mb:.1f} MB)")

    print("\nACX Upload Checklist:")
    print("  1. Upload individual chapter files (00_opening, 01-XX chapters, 99_closing)")
    print("  2. Upload retail sample file (bookN_sample.mp3)")
    print("  3. Set narrator as 'Nova (Virtual Voice)'")
    print("  4. Mark as AI-narrated in ACX submission form")
    print("  5. Complete audiobook file (bookN_complete.mp3) is for Findaway/Google Play")
