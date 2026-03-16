#!/usr/bin/env python3
"""
build_audiobook.py -- Full-cast AI audiobook generator for
"Beyond the Veil: A Quantum Western Thriller" (Hailey Pink Chronicles, Book 1).

Uses Microsoft Edge TTS (free neural voices) with unique voice per character.
Parses dialogue attribution to assign character voices automatically.

Voice Cast:
  Narrator    - en-US-GuyNeural      (deep male, Morrison-style)
  Hailey Pink - en-US-JennyNeural    (young female, 22)
  Jake        - en-US-EricNeural     (male, aggressive tone)
  Dr. Voss    - en-US-AriaNeural     (professional female)
  Mrs. Cooper - en-GB-SoniaNeural    (elderly female, wise)
  Sheriff Hart- en-US-RogerNeural    (gruff older male)
  Pete        - en-US-ChristopherNeural (working-class male)
  Mrs. Delgado- en-US-MichelleNeural (flat, subdued female)
  Minor Male  - en-US-BrianNeural
  Minor Female- en-US-EmmaNeural

Usage:
    python3 build_audiobook.py              # Build all chapters
    python3 build_audiobook.py --chapter 1  # Build single chapter
    python3 build_audiobook.py --test       # Quick test with prologue only

Output:
    audiobook/ch00_prologue.mp3
    audiobook/ch01_a_world_in_conflict.mp3
    ...
    audiobook/BEYOND_THE_VEIL_FULL_AUDIOBOOK.mp3
"""

import asyncio
import os
import re
import sys
import time
import glob as globmod
import subprocess
import tempfile
import shutil
from pathlib import Path

import edge_tts

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CHAPTERS_DIR = BASE_DIR / "chapters"
OUTPUT_DIR = BASE_DIR / "audiobook"
CHAPTER_FILES = sorted(CHAPTERS_DIR.glob("*.md"))

# ---------------------------------------------------------------------------
# Voice Cast Configuration
# ---------------------------------------------------------------------------
VOICE_CAST = {
    "narrator": {
        "voice": "en-US-GuyNeural",
        "rate": "-5%",
        "pitch": "-2Hz",
        "label": "Narrator"
    },
    "hailey": {
        "voice": "en-US-JennyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "label": "Hailey Pink"
    },
    "jake": {
        "voice": "en-US-EricNeural",
        "rate": "-8%",
        "pitch": "-4Hz",
        "label": "Jake"
    },
    "voss": {
        "voice": "en-US-AriaNeural",
        "rate": "-3%",
        "pitch": "-1Hz",
        "label": "Dr. Elena Voss"
    },
    "cooper": {
        "voice": "en-GB-SoniaNeural",
        "rate": "-10%",
        "pitch": "-3Hz",
        "label": "Mrs. Cooper"
    },
    "hart": {
        "voice": "en-US-RogerNeural",
        "rate": "-8%",
        "pitch": "-5Hz",
        "label": "Sheriff Hart"
    },
    "pete": {
        "voice": "en-US-ChristopherNeural",
        "rate": "-3%",
        "pitch": "-2Hz",
        "label": "Pete"
    },
    "delgado": {
        "voice": "en-US-MichelleNeural",
        "rate": "-12%",
        "pitch": "-1Hz",
        "label": "Mrs. Delgado"
    },
    "minor_male": {
        "voice": "en-US-BrianNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "label": "Minor Male"
    },
    "minor_female": {
        "voice": "en-US-EmmaNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "label": "Minor Female"
    },
    "timeline_woman": {
        "voice": "en-GB-LibbyNeural",
        "rate": "-8%",
        "pitch": "-2Hz",
        "label": "Timeline Woman"
    },
    "drift": {
        "voice": "en-US-SteffanNeural",
        "rate": "-15%",
        "pitch": "-8Hz",
        "label": "The Drift"
    },
}

# ---------------------------------------------------------------------------
# Character Detection Patterns
# ---------------------------------------------------------------------------
# Maps character name patterns to voice keys
CHARACTER_PATTERNS = {
    "hailey": [
        r"\bhailey\b", r"\bshe\s+said\b", r"\bshe\s+whispered\b",
        r"\bshe\s+murmured\b", r"\bshe\s+muttered\b", r"\bshe\s+called\b",
        r"\bshe\s+answered\b", r"\bshe\s+replied\b", r"\bshe\s+asked\b",
        r"\bshe\s+breathed\b", r"\bshe\s+managed\b", r"\bshe\s+told\b",
        r"\bher\s+voice\b", r"\bdeputy\s+pink\b", r"\bpink\s+said\b",
    ],
    "jake": [
        r"\bjake\b", r"\bjake\s+said\b", r"\bjake\s+muttered\b",
        r"\bjake\s+slurred\b", r"\bjake\s+snapped\b", r"\bjake\s+growled\b",
        r"\bjake\s+whispered\b", r"\bhe\s+said\b(?!.*sheriff)(?!.*hart)(?!.*pete)",
        r"\bjake\s+called\b", r"\bjake\s+asked\b",
    ],
    "voss": [
        r"\bvoss\b", r"\belena\b", r"\bdoctor\b", r"\bdr\.\s*voss\b",
        r"\bvoss\s+said\b", r"\bdoctor\s+said\b",
    ],
    "cooper": [
        r"\bcooper\b", r"\bmrs\.\s*cooper\b", r"\bold\s+woman\b",
        r"\bcooper\s+said\b", r"\bcooper\s+whispered\b",
    ],
    "hart": [
        r"\bhart\b", r"\bsheriff\b", r"\bsheriff\s+said\b",
        r"\bhart\s+said\b", r"\bsheriff\s+hart\b",
    ],
    "pete": [
        r"\bpete\b", r"\bpete\s+said\b", r"\bpete\s+muttered\b",
        r"\bpete\s+whispered\b",
    ],
    "delgado": [
        r"\bdelgado\b", r"\bmrs\.\s*delgado\b",
    ],
    "timeline_woman": [
        r"\bthe\s+woman\s+said\b", r"\bwoman\s+smiled\b",
        r"\bwoman\s+tilted\b", r"\bwoman\s+said\b",
    ],
}

# Attribution verbs that indicate someone is speaking
ATTRIBUTION_VERBS = [
    "said", "asked", "whispered", "murmured", "muttered", "called",
    "shouted", "yelled", "replied", "answered", "breathed", "managed",
    "continued", "added", "snapped", "growled", "slurred", "told",
    "demanded", "pleaded", "begged", "screamed", "hissed", "sighed",
    "croaked", "rasped", "stammered", "stuttered", "insisted",
]


# ---------------------------------------------------------------------------
# Text Processing
# ---------------------------------------------------------------------------

def clean_markdown(text):
    """Strip markdown formatting for TTS."""
    # Remove headers
    text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    # Remove cipher footers (. . . and encoded text)
    text = re.sub(r'^\s*\.\s*\.\s*\.\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[~+*^#@&%!=;:/\\()[\]{}|<>_\'".\s-]{5,}$', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers but keep text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Convert -- to em dash for natural reading
    text = text.replace(' -- ', ' \u2014 ')
    # Remove **END OF BOOK** markers
    text = re.sub(r'\*?\*?END OF BOOK.*?\*?\*?', '', text, flags=re.IGNORECASE)
    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def split_into_segments(text):
    """
    Split text into narration and dialogue segments.
    Returns list of dicts: {"type": "narration"|"dialogue", "text": str, "context": str}
    Context is the surrounding text for speaker attribution.
    """
    segments = []
    # Pattern to find quoted dialogue
    # Matches "text" or 'text' (but not possessives like it's)
    dialogue_pattern = re.compile(
        r'(?<![a-zA-Z])"([^"]{2,})"'  # Double-quoted dialogue
    )

    pos = 0
    for match in dialogue_pattern.finditer(text):
        # Narration before this dialogue
        if match.start() > pos:
            narr_text = text[pos:match.start()].strip()
            if narr_text:
                segments.append({
                    "type": "narration",
                    "text": narr_text,
                    "context": ""
                })

        # The dialogue itself
        dialogue_text = match.group(1).strip()
        # Get surrounding context for attribution (100 chars before and after)
        ctx_start = max(0, match.start() - 100)
        ctx_end = min(len(text), match.end() + 100)
        context = text[ctx_start:ctx_end]

        if dialogue_text:
            segments.append({
                "type": "dialogue",
                "text": dialogue_text,
                "context": context
            })

        pos = match.end()

    # Remaining narration after last dialogue
    if pos < len(text):
        remaining = text[pos:].strip()
        if remaining:
            segments.append({
                "type": "narration",
                "text": remaining,
                "context": ""
            })

    # If no dialogue found, treat entire text as narration
    if not segments:
        segments.append({
            "type": "narration",
            "text": text,
            "context": ""
        })

    return segments


def identify_speaker(context, last_speaker=None):
    """
    Identify who is speaking based on attribution context.
    Returns a voice key from VOICE_CAST.
    """
    context_lower = context.lower()

    # Score each character based on pattern matches in context
    scores = {}
    for char_key, patterns in CHARACTER_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, context_lower):
                score += 1
        if score > 0:
            scores[char_key] = score

    if scores:
        # Return highest scoring character
        best = max(scores, key=scores.get)
        return best

    # Fallback: if context has "he said/he ..." and last speaker was male
    if re.search(r'\bhe\s+(' + '|'.join(ATTRIBUTION_VERBS) + r')', context_lower):
        if last_speaker in ["jake", "hart", "pete", "minor_male"]:
            return last_speaker
        return "minor_male"

    if re.search(r'\bshe\s+(' + '|'.join(ATTRIBUTION_VERBS) + r')', context_lower):
        if last_speaker in ["hailey", "voss", "cooper", "delgado", "minor_female"]:
            return last_speaker
        return "hailey"  # Default female speaker is protagonist

    # If no attribution found, return last speaker or default
    return last_speaker or "hailey"


def parse_chapter_for_audio(filepath):
    """
    Parse a chapter file into audio segments with voice assignments.
    Returns: (chapter_title, list of {voice_key, text})
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract chapter title from first heading
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    chapter_title = title_match.group(1) if title_match else filepath.stem

    # Clean the markdown
    cleaned = clean_markdown(content)

    # Split into paragraphs
    paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]

    audio_segments = []
    last_speaker = None

    for para in paragraphs:
        # Skip very short paragraphs that are just formatting artifacts
        if len(para) < 3:
            continue

        # Split paragraph into narration/dialogue segments
        segments = split_into_segments(para)

        for seg in segments:
            if seg["type"] == "narration":
                audio_segments.append({
                    "voice_key": "narrator",
                    "text": seg["text"]
                })
            else:
                # Identify speaker from context
                speaker = identify_speaker(seg["context"], last_speaker)
                last_speaker = speaker
                audio_segments.append({
                    "voice_key": speaker,
                    "text": seg["text"]
                })

    return chapter_title, audio_segments


# ---------------------------------------------------------------------------
# Audio Generation
# ---------------------------------------------------------------------------

def generate_silence(output_path, duration_sec=1.5):
    """Generate a silent MP3 file using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"anullsrc=r=44100:cl=mono",
        "-t", str(duration_sec),
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, text=True)


def sanitize_for_tts(text):
    """Clean text so TTS can speak it without errors."""
    # Remove lines that are just symbols/punctuation
    text = re.sub(r'^[^a-zA-Z0-9]*$', '', text, flags=re.MULTILINE)
    # Remove stray markdown artifacts
    text = text.replace('#', '').replace('*', '')
    # Remove cipher-like strings (mostly symbols)
    text = re.sub(r'[~+^@&%!=;:/\\()[\]{}|<>_]{3,}', '', text)
    # Clean excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def generate_audio_segment(text, voice_config, output_path):
    """Generate a single audio segment using edge-tts."""
    # Sanitize text
    text = sanitize_for_tts(text)
    # Skip if text is too short or has no speakable content
    if not text or len(text) < 2 or not re.search(r'[a-zA-Z]', text):
        generate_silence(output_path, 0.5)
        return

    try:
        communicate = edge_tts.Communicate(
            text,
            voice_config["voice"],
            rate=voice_config.get("rate", "+0%"),
            pitch=voice_config.get("pitch", "+0Hz"),
        )
        await communicate.save(output_path)
    except Exception as e:
        print(f"\n    WARNING: TTS failed for segment ({str(e)[:60]}), inserting silence")
        generate_silence(output_path, 0.5)


async def build_chapter_audio(chapter_file, output_mp3, chapter_num=0):
    """Build a complete chapter audio file from segments."""
    chapter_title, segments = parse_chapter_for_audio(chapter_file)
    print(f"\n  Chapter: {chapter_title}")
    print(f"  Segments: {len(segments)}")

    if not segments:
        print("  WARNING: No segments found, skipping.")
        return None

    # Count voices used
    voices_used = set()
    for seg in segments:
        voices_used.add(seg["voice_key"])
    voice_labels = [VOICE_CAST[v]["label"] for v in voices_used]
    print(f"  Voices: {', '.join(voice_labels)}")

    # Create temp directory for segment audio files
    tmpdir = tempfile.mkdtemp(prefix=f"audiobook_ch{chapter_num:02d}_")

    try:
        # Generate chapter title announcement
        title_file = os.path.join(tmpdir, "000_title.mp3")
        title_text = chapter_title
        await generate_audio_segment(
            title_text,
            VOICE_CAST["narrator"],
            title_file
        )

        # Add a pause after title (2 seconds of silence)
        pause_file = os.path.join(tmpdir, "000_pause.mp3")
        generate_silence(pause_file, 2.0)

        # Generate each segment
        segment_files = [title_file, pause_file]
        total = len(segments)
        batch_size = 5  # Process in small batches to avoid rate limits

        for i in range(0, total, batch_size):
            batch = segments[i:i+batch_size]
            tasks = []

            for j, seg in enumerate(batch):
                idx = i + j + 1
                seg_file = os.path.join(tmpdir, f"{idx:04d}_seg.mp3")
                voice_config = VOICE_CAST[seg["voice_key"]]
                tasks.append(generate_audio_segment(
                    seg["text"], voice_config, seg_file
                ))
                segment_files.append(seg_file)

            # Run batch concurrently
            await asyncio.gather(*tasks)

            # Progress
            done = min(i + batch_size, total)
            pct = int(done / total * 100)
            print(f"    [{pct:3d}%] Generated {done}/{total} segments", end='\r')

        print(f"    [100%] Generated {total}/{total} segments")

        # Concatenate all segments using ffmpeg
        concat_list = os.path.join(tmpdir, "concat.txt")
        with open(concat_list, 'w') as f:
            for seg_file in segment_files:
                if os.path.exists(seg_file) and os.path.getsize(seg_file) > 0:
                    f.write(f"file '{seg_file}'\n")

        # Use ffmpeg to concatenate
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-ar", "44100", "-ac", "1",
            str(output_mp3)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: ffmpeg failed: {result.stderr[:200]}")
            return None

        # Get duration
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "csv=p=0", str(output_mp3)
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        size_mb = os.path.getsize(output_mp3) / (1024 * 1024)

        print(f"  Output: {output_mp3.name} ({minutes}m {seconds}s, {size_mb:.1f} MB)")
        return output_mp3

    finally:
        # Cleanup temp files
        shutil.rmtree(tmpdir, ignore_errors=True)


async def build_full_audiobook(chapter_indices=None):
    """Build the complete audiobook, chapter by chapter."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("BEYOND THE VEIL - Full-Cast Audiobook Generator")
    print("=" * 60)
    print(f"\nVoice Cast:")
    for key, config in VOICE_CAST.items():
        print(f"  {config['label']:20s} -> {config['voice']}")
    print(f"\nChapter files: {len(CHAPTER_FILES)}")
    print(f"Output dir: {OUTPUT_DIR}")

    chapter_mp3s = []
    files_to_process = []

    for i, chapter_file in enumerate(CHAPTER_FILES):
        if chapter_indices is not None and i not in chapter_indices:
            continue
        files_to_process.append((i, chapter_file))

    start_time = time.time()

    for i, chapter_file in files_to_process:
        output_name = f"ch{i:02d}_{chapter_file.stem}.mp3"
        output_path = OUTPUT_DIR / output_name

        result = await build_chapter_audio(chapter_file, output_path, i)
        if result:
            chapter_mp3s.append(result)

    # Combine all chapters into one audiobook file
    if len(chapter_mp3s) > 1:
        print(f"\n{'=' * 60}")
        print("Combining chapters into full audiobook...")
        full_audiobook = OUTPUT_DIR / "BEYOND_THE_VEIL_FULL_AUDIOBOOK.mp3"

        concat_list = OUTPUT_DIR / "_concat_full.txt"
        with open(concat_list, 'w') as f:
            for mp3 in chapter_mp3s:
                f.write(f"file '{mp3}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-ar", "44100", "-ac", "1",
            str(full_audiobook)
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        os.remove(concat_list)

        if full_audiobook.exists():
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "csv=p=0", str(full_audiobook)
            ]
            probe = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            size_mb = os.path.getsize(full_audiobook) / (1024 * 1024)
            print(f"\nFull audiobook: {full_audiobook}")
            print(f"Duration: {hours}h {minutes}m")
            print(f"Size: {size_mb:.1f} MB")

    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)
    print(f"\n{'=' * 60}")
    print(f"BUILD COMPLETE in {elapsed_min}m {elapsed_sec}s")
    print(f"Chapter files: {OUTPUT_DIR}/ch*.mp3")
    if len(chapter_mp3s) > 1:
        print(f"Full audiobook: {OUTPUT_DIR}/BEYOND_THE_VEIL_FULL_AUDIOBOOK.mp3")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Build full-cast audiobook for Beyond the Veil"
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Build only this chapter (0=prologue, 1-10=chapters)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Quick test: build only the prologue"
    )
    parser.add_argument(
        "--list-voices", action="store_true",
        help="List available voices and exit"
    )
    args = parser.parse_args()

    if args.list_voices:
        async def show():
            voices = await edge_tts.list_voices()
            en = [v for v in voices if v['Locale'].startswith('en-')]
            for v in en:
                print(f"{v['ShortName']:40s} {v['Gender']:8s}")
        asyncio.run(show())
        return

    if args.test:
        asyncio.run(build_full_audiobook(chapter_indices=[0]))
    elif args.chapter is not None:
        asyncio.run(build_full_audiobook(chapter_indices=[args.chapter]))
    else:
        asyncio.run(build_full_audiobook())


if __name__ == "__main__":
    main()
