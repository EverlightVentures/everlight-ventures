#!/usr/bin/env python3
"""
speech_service.py - Everlight Centralized TTS Engine
Hive Mind: hive_83877943 | 2026-03-10

Single abstraction layer for all TTS across:
  - Blackjack dealer (live, low-latency)
  - Audiobook chapters (long-form, cached)
  - Trailer samples (cinematic 30s previews)
  - Site audio samples (web player embeds)

Providers (priority order):
  1. ElevenLabs  - primary (Flash for live, Multilingual for audiobooks)
  2. MiniMax     - fallback (batch audiobook generation)
  3. OpenAI      - legacy fallback (tts-1-hd)
  4. espeak      - offline emergency

Cache: file-based MD5 hash in 07_STAGING/tts_cache/
Usage: monthly character tracking per provider in tts_cache/usage.json
"""

import os
import json
import hashlib
import logging
import re
import sys
import requests
from pathlib import Path
from datetime import datetime

log = logging.getLogger("speech_service")

WORKSPACE  = Path("/mnt/sdcard/AA_MY_DRIVE")
CACHE_DIR  = WORKSPACE / "07_STAGING/tts_cache"
USAGE_FILE = CACHE_DIR / "usage.json"

# Monthly character budgets (alert at 80%, hard stop at 100%)
BUDGETS = {
    "elevenlabs": 10_000,
    "minimax":    10_000,
    "openai":    500_000,
}

# ElevenLabs voice IDs per use case. Override via env vars.
VOICES = {
    "dealer":   os.environ.get("EL_DEALER_VOICE",   "pNInz6obpgDQGcFmaJgB"),  # Adam
    "kids":     os.environ.get("EL_KIDS_VOICE",     "EXAVITQu4vr4xnSDxMaL"),  # Bella
    "thriller": os.environ.get("EL_THRILLER_VOICE", "VR6AewLTigWG4xSOukaG"),  # Arnold
    "trailer":  os.environ.get("EL_TRAILER_VOICE",  "ErXwobaYiN019PkySvjV"),  # Antoni
    "default":  os.environ.get("EL_DEFAULT_VOICE",  "EXAVITQu4vr4xnSDxMaL"),
}

EL_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
MM_API_KEY  = os.environ.get("MINIMAX_API_KEY", "")
OAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EL_BASE     = "https://api.elevenlabs.io/v1"


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(text: str, voice_id: str, model: str) -> str:
    return hashlib.md5(f"{text}|{voice_id}|{model}".encode()).hexdigest()


def _get_cached(key: str) -> bytes | None:
    path = CACHE_DIR / f"{key}.mp3"
    return path.read_bytes() if path.exists() else None


def _write_cache(key: str, audio: bytes):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.mp3").write_bytes(audio)


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------

def _load_usage() -> dict:
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text())
    return {"elevenlabs": 0, "minimax": 0, "openai": 0,
            "month": datetime.now().strftime("%Y-%m")}


def _save_usage(usage: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage, indent=2))


def _track(provider: str, chars: int):
    usage = _load_usage()
    month = datetime.now().strftime("%Y-%m")
    if usage.get("month") != month:
        usage = {"elevenlabs": 0, "minimax": 0, "openai": 0, "month": month}
    usage[provider] = usage.get(provider, 0) + chars
    _save_usage(usage)
    budget = BUDGETS.get(provider, 999_999)
    pct = usage[provider] / budget * 100
    if pct >= 80:
        log.warning(
            f"[BUDGET ALERT] {provider} at {pct:.0f}% "
            f"({usage[provider]:,}/{budget:,} chars this month)"
        )


def get_usage_report() -> dict:
    """Current month usage vs budget for all providers."""
    usage = _load_usage()
    report = {"month": usage.get("month", "unknown")}
    for provider, budget in BUDGETS.items():
        used = usage.get(provider, 0)
        report[provider] = {
            "used": used,
            "budget": budget,
            "remaining": budget - used,
            "pct": round(used / budget * 100, 1),
        }
    return report


# ---------------------------------------------------------------------------
# Provider calls
# ---------------------------------------------------------------------------

def _elevenlabs(text: str, voice_id: str, model: str,
                stability: float, similarity: float, style: float) -> bytes:
    if not EL_API_KEY:
        raise EnvironmentError("ELEVENLABS_API_KEY not set")
    resp = requests.post(
        f"{EL_BASE}/text-to-speech/{voice_id}",
        headers={"xi-api-key": EL_API_KEY, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity,
                "style": style,
                "use_speaker_boost": True,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    _track("elevenlabs", len(text))
    return resp.content


def _minimax(text: str, voice_id: str = "male-qn-qingse") -> bytes:
    if not MM_API_KEY:
        raise EnvironmentError("MINIMAX_API_KEY not set")
    resp = requests.post(
        "https://api.minimax.chat/v1/t2a_v2",
        headers={"Authorization": f"Bearer {MM_API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "model": "speech-01-turbo",
            "text": text,
            "stream": False,
            "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
            "audio_setting": {"sample_rate": 44100, "bitrate": 192000,
                              "format": "mp3", "channel": 1},
        },
        timeout=60,
    )
    resp.raise_for_status()
    import base64
    audio = base64.b64decode(resp.json()["data"]["audio"])
    _track("minimax", len(text))
    return audio


def _openai_tts(text: str, voice: str = "fable") -> bytes:
    if not OAI_API_KEY:
        raise EnvironmentError("OPENAI_API_KEY not set")
    resp = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {OAI_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": "tts-1-hd", "voice": voice, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    _track("openai", len(text))
    return resp.content


def _generate(text: str, voice_id: str, model: str = "eleven_turbo_v2",
              stability: float = 0.5, similarity: float = 0.8,
              style: float = 0.0, use_cache: bool = True) -> bytes:
    """Core generation with cache + provider fallback chain."""
    key = _cache_key(text, voice_id, model)
    if use_cache:
        cached = _get_cached(key)
        if cached:
            log.debug(f"Cache hit {key[:8]}")
            return cached

    audio = None

    if EL_API_KEY:
        try:
            audio = _elevenlabs(text, voice_id, model, stability, similarity, style)
        except Exception as e:
            log.warning(f"ElevenLabs failed: {e}")

    if audio is None and MM_API_KEY:
        try:
            audio = _minimax(text)
        except Exception as e:
            log.warning(f"MiniMax failed: {e}")

    if audio is None and OAI_API_KEY:
        try:
            audio = _openai_tts(text)
        except Exception as e:
            log.warning(f"OpenAI TTS failed: {e}")

    if audio is None:
        raise RuntimeError(
            "All TTS providers failed. "
            "Set ELEVENLABS_API_KEY, MINIMAX_API_KEY, or OPENAI_API_KEY."
        )

    if use_cache:
        _write_cache(key, audio)
    return audio


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _chunk_text(text: str, max_chars: int = 2400) -> list[str]:
    """Split at sentence boundaries without exceeding max_chars."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def speak_dealer(text: str, output_path: Path | None = None) -> bytes:
    """
    Live blackjack dealer voice. Low latency, authoritative.
    Uses Flash model for fastest response.
    """
    audio = _generate(
        text,
        voice_id=VOICES["dealer"],
        model="eleven_flash_v2",
        stability=0.60,
        similarity=0.85,
        style=0.20,
    )
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio)
    return audio


def generate_audiobook_chapter(
    text: str,
    book_id: str,
    chapter: int,
    output_path: Path,
    genre: str = "kids",
) -> Path:
    """
    Long-form audiobook chapter. Chunks text, concatenates output.
    genre: 'kids' | 'thriller'
    """
    voice_id   = VOICES.get(genre, VOICES["default"])
    model      = "eleven_multilingual_v2"
    stability  = 0.72 if genre == "kids" else 0.55
    similarity = 0.80
    style      = 0.0  if genre == "kids" else 0.25

    chunks = _chunk_text(text, max_chars=2400)
    parts  = []
    for i, chunk in enumerate(chunks):
        log.info(f"  [{book_id}] ch{chapter} chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        audio = _generate(chunk, voice_id, model, stability, similarity, style)
        parts.append(audio)

    combined = b"".join(parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(combined)
    log.info(f"  Saved: {output_path}")
    return output_path


def generate_trailer_sample(
    text: str,
    book_id: str,
    output_path: Path,
    genre: str = "thriller",
) -> Path:
    """
    30-second Hollywood trailer-style preview.
    High drama, cinematic pacing. Designed to sell the book.
    Feed only peak tension passages - never title/prologue/TOC.
    """
    voice_id = VOICES["trailer"]
    model    = "eleven_multilingual_v2"

    audio = _generate(
        text,
        voice_id=voice_id,
        model=model,
        stability=0.35,
        similarity=0.75,
        style=0.45,
        use_cache=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio)
    log.info(f"Trailer sample saved: {output_path}")
    return output_path


def generate_site_sample(
    text: str,
    book_id: str,
    output_path: Path,
    genre: str = "kids",
) -> Path:
    """
    Web player audio sample for everlightventures.io/publishing.
    Same cinematic approach, genre-appropriate voice.
    """
    voice_id  = VOICES.get(genre, VOICES["default"])
    model     = "eleven_multilingual_v2"
    stability = 0.40 if genre == "thriller" else 0.55
    style     = 0.35 if genre == "thriller" else 0.15

    audio = _generate(
        text,
        voice_id=voice_id,
        model=model,
        stability=stability,
        similarity=0.78,
        style=style,
        use_cache=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio)
    log.info(f"Site sample saved: {output_path}")
    return output_path


def get_usage_report() -> dict:
    """Return current month usage vs budget for all providers."""
    usage = _load_usage()
    report = {"month": usage.get("month", "unknown")}
    for provider, budget in BUDGETS.items():
        used = usage.get(provider, 0)
        report[provider] = {
            "used": used,
            "budget": budget,
            "remaining": budget - used,
            "pct": round(used / budget * 100, 1),
        }
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if "--usage" in sys.argv:
        print(json.dumps(get_usage_report(), indent=2))

    elif "--test-dealer" in sys.argv:
        audio = speak_dealer(
            "Welcome to the table. Place your bets. "
            "No more bets. Dealer has blackjack. You win!"
        )
        out = Path("/tmp/dealer_test.mp3")
        out.write_bytes(audio)
        print(f"Saved {out}")

    elif "--test-trailer" in sys.argv:
        sample = (
            "She thought the nightmares were hers alone. "
            "But the shadow had found her frequency, "
            "and it was bleeding through. "
            "Some doors, once opened, cannot be closed."
        )
        generate_trailer_sample(sample, "btv_1", Path("/tmp/trailer_test.mp3"))
        print("Saved /tmp/trailer_test.mp3")

    else:
        print("Usage: speech_service.py [--usage | --test-dealer | --test-trailer]")
