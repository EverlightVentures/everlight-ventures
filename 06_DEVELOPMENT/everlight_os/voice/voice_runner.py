"""voice_runner -- press-to-talk → whisper.cpp → clipboard / type / pipe.

Capture audio via PipeWire (pw-record), transcribe locally with whisper.cpp,
output to clipboard (wl-copy), terminal (xdotool/ydotool), or named pipe.

Designed to bind to a KDE global shortcut (Meta+Space recommended). Single
invocation per voice command -- no always-on listening.

Usage:
    # Record for 5s, transcribe, copy to clipboard
    voice_runner.py --capture --duration 5 --clip

    # Push-to-talk (record while invocation runs, until you press Ctrl+C OR --duration hits)
    voice_runner.py --capture --duration 10 --clip --type

    # Pipe transcript into a named pipe (Claude CLI tails this)
    voice_runner.py --capture --duration 8 --pipe /tmp/voice_to_cli.fifo

    # Just output transcript to stdout
    voice_runner.py --capture --duration 5

Requires: pw-record (PipeWire), whisper-cli (whisper.cpp), wl-copy (wl-clipboard)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

VOICE_ROOT = Path("/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/voice")
MODELS_DIR = VOICE_ROOT / "models"
DEFAULT_MODEL = MODELS_DIR / "ggml-small.en.bin"

log = logging.getLogger("voice_runner")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


def _audit(action_type: str, payload: dict) -> None:
    try:
        sys.path.insert(0, "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance")
        from audit_log import write_envelope  # type: ignore
        write_envelope(agent_id="voice_runner", action_type=action_type, payload=payload)
    except Exception:
        pass


def record_audio(out_path: Path, duration: float = 5.0) -> bool:
    """Record `duration` seconds of audio via pw-record (PipeWire native).
    Output is 16kHz mono WAV (whisper.cpp's preferred format)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("recording %ss to %s", duration, out_path)
    try:
        # pw-record can output WAV directly with --rate + --format + --channels
        proc = subprocess.run(
            ["pw-record",
             "--target=@DEFAULT_AUDIO_SOURCE@",
             "--rate", "16000",
             "--channels", "1",
             "--format", "s16",
             str(out_path)],
            timeout=duration + 2,
        )
        return out_path.exists() and out_path.stat().st_size > 1000
    except subprocess.TimeoutExpired:
        # Expected -- pw-record runs until killed; the timeout IS the duration
        return out_path.exists() and out_path.stat().st_size > 1000
    except Exception as e:
        log.error("pw-record failed: %s", e)
        return False


def transcribe(audio_path: Path, model_path: Path = DEFAULT_MODEL,
               threads: int = 4) -> str:
    """Run whisper.cpp on the WAV. Returns transcript string."""
    if not model_path.exists():
        log.error("model not found: %s", model_path)
        return ""
    if not audio_path.exists():
        log.error("audio file not found: %s", audio_path)
        return ""
    out_prefix = audio_path.with_suffix("")  # whisper-cli writes <prefix>.txt etc
    try:
        # whisper-cli: -m model -f input -otxt (output text)
        r = subprocess.run(
            ["whisper-cli",
             "-m", str(model_path),
             "-f", str(audio_path),
             "-t", str(threads),
             "-otxt",
             "-of", str(out_prefix),  # output prefix (no extension)
             "--no-prints"],
            capture_output=True, text=True, timeout=60,
        )
        txt_path = Path(f"{out_prefix}.txt")
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8", errors="replace").strip()
            try:
                txt_path.unlink()
            except Exception:
                pass
            return text
        # Fallback: parse stdout
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error("whisper-cli timed out")
        return ""
    except Exception as e:
        log.error("whisper-cli error: %s", e)
        return ""


def output_clip(text: str) -> bool:
    """Send text to clipboard (Wayland or X11 -- xdotool_safe handles fallback)."""
    sys.path.insert(0, "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use")
    import xdotool_safe as xs
    ok, det = xs.clipboard_write(text)
    if ok:
        log.info("copied %d chars to clipboard", len(text))
    else:
        log.error("clipboard write failed: %s", det)
    return ok


def output_type(text: str) -> bool:
    """Type text into focused window via xdotool_safe (handles xdotool/ydotool)."""
    sys.path.insert(0, "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use")
    import xdotool_safe as xs
    ok, det = xs.type_text(text, delay_ms=10)
    if ok:
        log.info("typed %d chars into focused window", len(text))
        return True
    log.warning("xdotool type failed (%s), trying ydotool", det)
    try:
        subprocess.run(["ydotool", "type", text], timeout=30, check=True)
        return True
    except Exception as e2:
        log.error("ydotool also failed: %s", e2)
        return False


def output_pipe(text: str, pipe_path: Path) -> bool:
    """Append text to a named pipe (Claude CLI tails this for input)."""
    try:
        with pipe_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
        return True
    except Exception as e:
        log.error("pipe write failed: %s", e)
        return False


def run_capture(duration: float, sinks: dict, model_path: Path = DEFAULT_MODEL) -> dict:
    """Record + transcribe + dispatch to all configured sinks. Returns summary dict."""
    started_at = time.time()
    audio = Path("/tmp") / f"voice_buf_{os.getpid()}.wav"
    try:
        ok = record_audio(audio, duration=duration)
        if not ok:
            return {"status": "failed", "error": "audio_record_failed"}

        text = transcribe(audio, model_path=model_path)
        if not text:
            return {"status": "failed", "error": "empty_transcript"}

        results = {}
        if sinks.get("clip"):
            results["clipboard"] = output_clip(text)
        if sinks.get("type"):
            results["typed"] = output_type(text)
        if sinks.get("pipe"):
            results["piped"] = output_pipe(text, Path(sinks["pipe"]))

        _audit("voice.transcript_captured", {
            "transcript_len": len(text),
            "preview": text[:80],
            "duration_seconds": duration,
            "elapsed": round(time.time() - started_at, 2),
            "sinks": list(sinks.keys()),
            "results": results,
        })

        return {
            "status": "done",
            "transcript": text,
            "elapsed_seconds": round(time.time() - started_at, 2),
            "sinks": results,
        }
    finally:
        try:
            audio.unlink(missing_ok=True)
        except Exception:
            pass


def _cli() -> int:
    p = argparse.ArgumentParser(description="voice_runner -- speak, transcribe, output")
    p.add_argument("--capture", action="store_true", help="Run capture mode")
    p.add_argument("--duration", type=float, default=5.0, help="Recording duration seconds")
    p.add_argument("--clip", action="store_true", help="Send to clipboard (wl-copy)")
    p.add_argument("--type", dest="type_out", action="store_true",
                   help="Type into focused window (xdotool)")
    p.add_argument("--pipe", default=None, help="Append to named pipe path")
    p.add_argument("--model", default=str(DEFAULT_MODEL), help="whisper model path")
    args = p.parse_args()

    if not args.capture:
        p.print_help()
        return 2

    sinks = {}
    if args.clip:
        sinks["clip"] = True
    if args.type_out:
        sinks["type"] = True
    if args.pipe:
        sinks["pipe"] = args.pipe
    if not sinks:
        sinks["stdout"] = True  # default: just print

    result = run_capture(args.duration, sinks, model_path=Path(args.model))
    print(json.dumps(result, indent=2))
    if "stdout" in sinks and result.get("transcript"):
        print(result["transcript"])
    return 0 if result.get("status") == "done" else 1


if __name__ == "__main__":
    sys.exit(_cli())
