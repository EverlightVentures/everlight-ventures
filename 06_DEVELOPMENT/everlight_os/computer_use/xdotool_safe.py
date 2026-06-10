"""xdotool_safe -- unified xdotool / wmctrl / xsel wrapper.

Single source of truth for synthetic input dispatch on KDE Plasma 6 Wayland.
Every other module imports from here instead of shelling out independently.

Why centralize:
  - Consistent timeout + retry semantics
  - Consistent DISPLAY env handling
  - Single place to add: telemetry, dry-run, fallback to ydotool, error classification
  - Easy to mock in tests

All public functions return a tuple (ok: bool, detail: str). Detail is the
stdout/stderr excerpt for debugging.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Optional

log = logging.getLogger("xdotool_safe")

DEFAULT_DISPLAY = os.environ.get("DISPLAY", ":1")
DEFAULT_TIMEOUT = 5.0


def _env() -> dict[str, str]:
    """Return a subprocess env dict with DISPLAY set."""
    return {**os.environ, "DISPLAY": DEFAULT_DISPLAY, "LC_ALL": "C"}


def _run(cmd: list[str], *, timeout: float = DEFAULT_TIMEOUT,
         input_text: Optional[str] = None) -> tuple[bool, str]:
    """Run a command. Returns (ok, output_excerpt)."""
    try:
        r = subprocess.run(
            cmd,
            env=_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
        )
        out = (r.stdout or r.stderr or "").strip()[:400]
        return (r.returncode == 0, out)
    except subprocess.TimeoutExpired:
        return (False, f"timeout after {timeout}s")
    except FileNotFoundError as e:
        return (False, f"binary not found: {e}")
    except Exception as e:
        return (False, f"error: {type(e).__name__}: {e}")


# ── Window queries ────────────────────────────────────────────────


def get_active_window_name() -> str:
    """Return the focused window's title (empty if unavailable)."""
    ok, out = _run(["xdotool", "getactivewindow", "getwindowname"], timeout=3.0)
    return out if ok else ""


def get_active_window_id() -> str:
    """Return the focused window's hex WID (empty if unavailable)."""
    ok, out = _run(["xdotool", "getactivewindow"], timeout=3.0)
    return out.strip() if ok else ""


def search_windows(name_regex: str) -> list[str]:
    """Search by title regex. Returns list of WIDs (decimal as strings)."""
    ok, out = _run(["xdotool", "search", "--name", name_regex], timeout=3.0)
    if not ok:
        return []
    return [w.strip() for w in out.splitlines() if w.strip()]


def list_windows() -> list[tuple[str, str]]:
    """Return [(wid_hex, title), ...] from wmctrl -l."""
    ok, out = _run(["wmctrl", "-l"], timeout=3.0)
    if not ok:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 4:
            rows.append((parts[0], parts[3]))
    return rows


def find_window_by_title(substring: str) -> Optional[str]:
    """Return first WID (hex) whose title contains `substring` (case-insensitive)."""
    needle = substring.lower()
    for wid, title in list_windows():
        if needle in title.lower():
            return wid
    return None


def get_cursor_position() -> tuple[int, int]:
    """Return (x, y) of mouse cursor. (0, 0) on failure."""
    ok, out = _run(["xdotool", "getmouselocation", "--shell"], timeout=3.0)
    if not ok:
        return (0, 0)
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            d[k.strip()] = v.strip()
    try:
        return (int(d.get("X", 0)), int(d.get("Y", 0)))
    except ValueError:
        return (0, 0)


# ── Window focus ──────────────────────────────────────────────────


def activate_window(wid: str, *, sync: bool = True) -> tuple[bool, str]:
    """Bring window to front (wmctrl is more reliable than xdotool on KDE)."""
    return _run(["wmctrl", "-ia", wid], timeout=3.0)


# ── Mouse ─────────────────────────────────────────────────────────


def mouse_move(x: int, y: int, *, sync: bool = False) -> tuple[bool, str]:
    args = ["xdotool", "mousemove"]
    if sync:
        args.append("--sync")
    args.extend([str(x), str(y)])
    return _run(args, timeout=3.0)


def mouse_click(button: int = 1, *, x: Optional[int] = None,
                y: Optional[int] = None, repeat: int = 1,
                modifier: str = "") -> tuple[bool, str]:
    """Click at (x, y) if given, else at current cursor. button: 1=left,
    2=middle, 3=right. modifier: 'shift', 'ctrl', 'alt', 'super', or empty."""
    if x is not None and y is not None:
        ok, det = mouse_move(x, y)
        if not ok:
            return (False, f"mousemove failed: {det}")
        time.sleep(0.05)
    if modifier:
        _run(["xdotool", "keydown", modifier], timeout=2.0)
    args = ["xdotool", "click"]
    if repeat > 1:
        args.extend(["--repeat", str(repeat)])
    args.append(str(button))
    ok, det = _run(args, timeout=3.0)
    if modifier:
        _run(["xdotool", "keyup", modifier], timeout=2.0)
    return (ok, det)


def mouse_down(button: int = 1) -> tuple[bool, str]:
    return _run(["xdotool", "mousedown", str(button)], timeout=2.0)


def mouse_up(button: int = 1) -> tuple[bool, str]:
    return _run(["xdotool", "mouseup", str(button)], timeout=2.0)


# ── Keyboard ──────────────────────────────────────────────────────


def key_press(key: str) -> tuple[bool, str]:
    """Single key or chord (e.g. 'Return', 'ctrl+l', 'Escape')."""
    return _run(["xdotool", "key", "--clearmodifiers", key], timeout=3.0)


def key_down(key: str) -> tuple[bool, str]:
    return _run(["xdotool", "keydown", key], timeout=2.0)


def key_up(key: str) -> tuple[bool, str]:
    return _run(["xdotool", "keyup", key], timeout=2.0)


def hold_key(key: str, duration: float) -> tuple[bool, str]:
    """Hold key for duration seconds."""
    ok, det = key_down(key)
    if not ok:
        return (False, det)
    time.sleep(min(duration, 10.0))
    return key_up(key)


def type_text(text: str, *, delay_ms: int = 12) -> tuple[bool, str]:
    """Type text into focused window. delay_ms = inter-keystroke delay."""
    return _run(
        ["xdotool", "type", "--clearmodifiers", "--delay", str(delay_ms), text],
        timeout=max(30.0, len(text) * 0.05),
    )


# ── Clipboard ─────────────────────────────────────────────────────


def clipboard_read() -> str:
    """Read current clipboard. Tries wl-paste, xsel, xclip in order."""
    for cmd in (["wl-paste"], ["xsel", "--clipboard", "--output"],
                ["xclip", "-selection", "clipboard", "-o"]):
        ok, out = _run(cmd, timeout=3.0)
        if ok and out:
            return out
    return ""


def clipboard_write(text: str) -> tuple[bool, str]:
    """Write text to clipboard. Tries wl-copy, xsel, xclip."""
    for cmd in (["wl-copy"], ["xsel", "--clipboard", "--input"],
                ["xclip", "-selection", "clipboard", "-i"]):
        ok, det = _run(cmd, timeout=3.0, input_text=text)
        if ok:
            return (True, det)
    return (False, "no working clipboard tool")


# ── High-level helpers ────────────────────────────────────────────


def focus_and_type(window_substring: str, text: str,
                   *, sleep_after_focus: float = 0.3) -> tuple[bool, str]:
    """Find a window by title substring, focus it, type the text."""
    wid = find_window_by_title(window_substring)
    if not wid:
        return (False, f"window not found: '{window_substring}'")
    ok, det = activate_window(wid)
    if not ok:
        return (False, f"activate failed: {det}")
    time.sleep(sleep_after_focus)
    return type_text(text)


def navigate_url_in_browser(url: str) -> tuple[bool, str]:
    """Generic Ctrl+L + type URL + Enter sequence in the focused browser."""
    ok, det = key_press("ctrl+l")
    if not ok:
        return (False, f"ctrl+l failed: {det}")
    time.sleep(0.3)
    ok, det = type_text(url)
    if not ok:
        return (False, f"type failed: {det}")
    time.sleep(0.2)
    return key_press("Return")


if __name__ == "__main__":
    # Smoke test
    print(f"DISPLAY={DEFAULT_DISPLAY}")
    print(f"active window: {get_active_window_name()!r}")
    print(f"cursor: {get_cursor_position()}")
    print(f"all windows: {len(list_windows())} found")
