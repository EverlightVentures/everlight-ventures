# Voice-to-Terminal -- Usage Guide
**Built:** 2026-05-06
**Stack:** PipeWire + whisper.cpp small.en + wl-copy / xdotool

## What it does

Press a global hotkey, speak into your mic, release/wait for duration. The transcript goes wherever you point it: your clipboard, the focused terminal, or a named pipe.

Designed to make voice replace keyboard for Claude CLI prompts.

## Quick test (no shortcut needed)

```bash
# Speak for 5 seconds, transcript copied to clipboard
/AA_MY_DRIVE/.venv/bin/python3 /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/voice/voice_runner.py \
    --capture --duration 5 --clip

# Then paste with middle-click or Ctrl+V
```

## Bind to KDE Global Shortcut (Meta+Space recommended)

1. Open **KDE System Settings** -> **Shortcuts** -> **Custom Shortcuts**
2. Click **Edit** -> **New** -> **Global Shortcut** -> **Command/URL**
3. Name: `Lucrex Voice -> Clipboard`
4. **Trigger** tab -> Click "None" -> press **Meta+Space** (or your preferred combo)
5. **Action** tab -> Command:
   ```
   /AA_MY_DRIVE/.venv/bin/python3 /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/voice/voice_runner.py --capture --duration 8 --clip
   ```
6. Apply

Now press Meta+Space -> speak for up to 8 seconds -> the transcript is on your clipboard.

## Command modes

| Mode | Flag | What it does |
|---|---|---|
| Clipboard | `--clip` | wl-copy the transcript. Paste with Ctrl+V. **Lowest friction.** |
| Type into terminal | `--type` | xdotool types directly into the focused window. Hands-free. |
| Named pipe | `--pipe /tmp/cli.fifo` | Append to a pipe Claude CLI tails (advanced) |
| Stdout | (default) | Print transcript only (debugging) |

You can combine: `--clip --type` writes to BOTH clipboard and focused window.

## Latency

| Step | Time |
|---|---|
| pw-record start | <100ms |
| Record duration | --duration arg |
| whisper.cpp small.en (5s clip, 4 cores) | ~1.5s |
| wl-copy / xdotool inject | <50ms |
| **Total: speak end -> text available** | **~1.5-2s** |

## Audit log

Every transcript writes a `voice.transcript_captured` envelope to `_audit/1L/voice_runner/`. The audio buffer is deleted from `/tmp` after transcription (never persisted). The transcript itself IS persisted -- don't speak credentials.

## Brake conditions

- Audio buffer deleted on every run
- No always-on listening (push-to-talk only)
- Whisper.cpp runs locally; nothing leaves the machine
- If transcript matches outbound-halt patterns and `WHOLESALE_OUTBOUND_HALT=1`, the auto-paste skips and posts a Slack warning

## Switching models

The default `ggml-small.en.bin` is 488MB and runs in ~1.5s for 5s of audio on CPU. If you want faster:
- `ggml-tiny.en.bin` (75MB, ~0.5s) -- less accurate, more typos
- `ggml-base.en.bin` (148MB, ~1.0s) -- good balance
- `ggml-medium.en.bin` (1.5GB, ~4s) -- most accurate, slowest

## Troubleshooting

**No audio captured:** check default mic with `pw-cli list-objects | grep -A2 source`.

**xdotool type fails (Wayland-native app):** install ydotool daemon: `sudo systemctl start ydotool`.

**Whisper too slow:** edit voice_runner.py and bump `threads=4` to `threads=8` in `transcribe()`.
