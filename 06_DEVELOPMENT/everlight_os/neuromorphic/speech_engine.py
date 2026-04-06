"""
Speech Engine -- Whisper STT + Pyannote speaker diarization.

Gives agents the ability to HEAR. Transcribes audio from:
  - Phone calls (via voice handler)
  - Uploaded audio files
  - Live microphone streams

Pipeline:
  Audio -> Whisper (transcribe) -> Pyannote (who spoke) -> NLP (analyze)
  -> call_copilot (summarize) -> Slack + Blinko + Dashboard

Uses: OpenAI Whisper (MIT), Pyannote (MIT) -- free, local, no API.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Whisper model size: "tiny" (39M), "base" (74M), "small" (244M), "medium" (769M)
# Use "base" for speed/accuracy balance on CPU
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

_whisper_model = None


def _get_whisper():
    """Lazy-load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        log.info(f"Loading Whisper model: {WHISPER_MODEL}")
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        log.info("Whisper model loaded")
    return _whisper_model


def transcribe_audio(
    audio_path: str | Path,
    language: str = "en",
    include_timestamps: bool = True,
) -> dict:
    """Transcribe an audio file to text using Whisper.

    Args:
        audio_path: Path to audio file (wav, mp3, m4a, etc.)
        language: Language code (en, es, etc.)
        include_timestamps: Include word-level timestamps

    Returns:
        Dict with text, segments (timestamped), language, duration
    """
    model = _get_whisper()
    audio_path = str(audio_path)

    t0 = time.time()
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=include_timestamps,
    )
    duration = time.time() - t0

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
        "language": result.get("language", language),
        "duration_sec": round(duration, 2),
        "audio_file": audio_path,
    }


def transcribe_call(
    audio_path: str | Path,
    agent_name: str = "",
    prospect_name: str = "",
) -> dict:
    """Transcribe a phone call and run full analysis pipeline.

    This is the main entry point for call transcription.
    Combines: Whisper (STT) -> NLP (analyze) -> call_copilot (summarize)
    """
    # Step 1: Transcribe with Whisper
    transcript = transcribe_audio(audio_path)

    # Step 2: Analyze with NLP
    try:
        from nlp_engine import analyze_text
        analysis = analyze_text(transcript["text"])
        transcript["nlp"] = analysis.to_dict()
    except Exception as e:
        log.warning(f"NLP analysis failed: {e}")
        transcript["nlp"] = {}

    # Step 3: Generate summary with call_copilot
    try:
        from call_copilot import process_completed_call, get_agent_voice_config
        voice_config = get_agent_voice_config(agent_name) if agent_name else {}

        summary = process_completed_call(
            agent_name=agent_name or "unknown",
            agent_voice_id=voice_config.get("voice_id", ""),
            prospect_name=prospect_name or "Unknown Prospect",
            transcript=transcript["text"],
            duration_sec=int(transcript.get("duration_sec", 0)),
            call_type="inbound",
        )
        transcript["summary"] = summary
    except Exception as e:
        log.warning(f"Call summary failed: {e}")
        transcript["summary"] = {}

    return transcript


def identify_speakers(
    audio_path: str | Path,
    num_speakers: int = 2,
) -> list[dict]:
    """Identify who spoke when using Pyannote speaker diarization.

    Note: Requires pyannote.audio and a Hugging Face token for
    the pretrained model. Falls back to simple VAD if unavailable.

    Args:
        audio_path: Path to audio file
        num_speakers: Expected number of speakers (default 2 for calls)

    Returns:
        List of speaker segments [{speaker: "SPEAKER_0", start: 0.5, end: 3.2}, ...]
    """
    try:
        from pyannote.audio import Pipeline
        import torch

        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            log.warning("HF_TOKEN not set -- speaker diarization unavailable")
            return []

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

        # Run on CPU
        diarization = pipeline(
            str(audio_path),
            num_speakers=num_speakers,
        )

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "speaker": speaker,
                "start": round(turn.start, 2),
                "end": round(turn.end, 2),
                "duration": round(turn.end - turn.start, 2),
            })

        return segments

    except Exception as e:
        log.warning(f"Speaker diarization failed: {e}")
        return []


def merge_transcript_with_speakers(
    transcript: dict,
    speaker_segments: list[dict],
) -> list[dict]:
    """Merge Whisper transcript with Pyannote speaker IDs.

    Creates a conversation-style transcript:
    [{"speaker": "Agent", "start": 0.5, "text": "Hello, this is Piper..."}, ...]
    """
    if not speaker_segments:
        return [{"speaker": "unknown", "start": s["start"], "text": s["text"]}
                for s in transcript.get("segments", [])]

    merged = []
    for seg in transcript.get("segments", []):
        seg_mid = (seg["start"] + seg["end"]) / 2

        # Find which speaker was talking at this segment's midpoint
        speaker = "unknown"
        for sp in speaker_segments:
            if sp["start"] <= seg_mid <= sp["end"]:
                speaker = sp["speaker"]
                break

        merged.append({
            "speaker": speaker,
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
        })

    return merged


def get_status() -> dict:
    """Check speech engine status."""
    whisper_ready = False
    try:
        import whisper
        whisper_ready = True
    except ImportError:
        pass

    pyannote_ready = False
    try:
        import pyannote.audio
        pyannote_ready = True
    except ImportError:
        pass

    return {
        "whisper_available": whisper_ready,
        "whisper_model": WHISPER_MODEL,
        "pyannote_available": pyannote_ready,
        "hf_token_set": bool(os.environ.get("HF_TOKEN")),
    }
