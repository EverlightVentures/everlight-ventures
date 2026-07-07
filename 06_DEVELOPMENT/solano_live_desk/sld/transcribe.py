from __future__ import annotations

# Local scanner-audio transcription with faster-whisper (free, runs on e5 ARM
# CPU). VAD filtering skips the long silences typical of scanner audio, so a
# 30-minute block transcribes far faster than its wall-clock length.
_MODEL = None


def _model(size: str):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel

        _MODEL = WhisperModel(size, device="cpu", compute_type="int8")
    return _MODEL


def transcribe_file(path: str, size: str = "base.en") -> list[dict]:
    """Return [{start, end, text}] segments for an audio file."""
    segments, _info = _model(size).transcribe(path, vad_filter=True, language="en")
    return [
        {"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()}
        for s in segments
        if s.text.strip()
    ]
