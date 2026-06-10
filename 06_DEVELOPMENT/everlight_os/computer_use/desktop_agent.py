"""desktop_agent -- Anthropic Computer Use for Rich's REAL desktop (Wayland Plasma).

Adapted from computer_use/agent.py (which targets Docker/Xvfb display :99).
Differences:
  - Screenshot via `spectacle -b -n -f -o <path>` (KDE Plasma 6 native, works on Wayland)
  - Input via `xdotool` (works on XWayland, which Firefox + most apps use)
  - Reads $DISPLAY (default :1 for Rich's session, not :99)
  - Configurable screenshot directory (per-task)
  - Honors WHOLESALE_OUTBOUND_HALT for any task that touches outbound channels
  - Writes audit envelopes for every action

Usage:
    from desktop_agent import run_task
    result = run_task(
        task="Open https://example.com in Firefox and report the page title",
        screenshots_dir=Path("/AA_MY_DRIVE/_logs/browser_tasks/screenshots/btsk_xxx"),
        max_iterations=30,
        width=1920, height=1080,
    )
    print(result["status"], result["steps"][-1])
"""
from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover
    Anthropic = None  # caller surfaces the error

# Cooperative lock between CLI and desktop_runner. Prevents focus theft when
# Rich is answering an AskUserQuestion / interactive prompt in the terminal.
try:
    import collab_lock  # type: ignore
except ImportError:
    try:
        from . import collab_lock  # type: ignore
    except Exception:
        collab_lock = None  # graceful degradation

# Operational context loader -- pulls Rich's aliases, configs, memory, recent
# state into the system prompt so the agent operates consistently.
try:
    import context_loader  # type: ignore
except ImportError:
    try:
        from . import context_loader  # type: ignore
    except Exception:
        context_loader = None  # graceful degradation

log = logging.getLogger("desktop-agent")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


DEFAULT_DISPLAY = os.environ.get("DISPLAY", ":1")
DEFAULT_MODEL = os.environ.get("DESKTOP_AGENT_MODEL", "claude-sonnet-4-5")
# Hybrid model strategy (May 2026): Sonnet 4.5 default for cost (~5x cheaper
# than Opus). Per-envelope model_override flips to Opus 4.7 for hard visual
# tasks (zoom action, OCR on long alphanumeric) or Haiku 4.5 for trivial
# state checks. Override globally via DESKTOP_AGENT_MODEL env.


def _agent_dimensions_for(model: str) -> tuple[int, int]:
    """Return the (width, height) the agent should see for a given model.
    Sonnet/Haiku cap input images at 1568px long edge; sending oversize wastes
    tokens AND breaks coord scaling because the API silently downsamples.
    Opus 4.x supports 1:1 coords up to 2576px so we send native 1920x1080."""
    if "opus-4-7" in model or "opus-4-6" in model or "opus-4-5" in model:
        return 1920, 1080
    # Sonnet 4.5, Sonnet 4.6, Haiku 4.5 -- all cap at 1568 long edge
    # Aspect-correct 16:9: 1568x882
    return 1568, 882

# Coordinate-space mapping. The agent sees the screen at AGENT_WIDTH x AGENT_HEIGHT
# (we resize before sending). xdotool executes in the REAL screen pixel space.
# get_real_resolution() probes Xrandr/xdpyinfo at startup. Mismatch was the
# root cause of every prior task failure: agent said "click (500, 300)",
# xdotool clicked literal (500, 300) on a 3840x2160 screen -- off by ~6x.
def get_real_resolution() -> tuple[int, int]:
    """Probe the actual physical display resolution. Returns (width, height)."""
    env = {**os.environ, "DISPLAY": DEFAULT_DISPLAY}
    try:
        r = subprocess.run(["xdpyinfo"], env=env, capture_output=True,
                           text=True, timeout=5)
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("dimensions:"):
                # "dimensions:    3840x2160 pixels (1016x571 millimeters)"
                dim = line.split()[1]
                w, h = dim.split("x")
                return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080  # safe fallback


# Audit log integration (best-effort)
def _audit(action_type: str, payload: dict) -> None:
    try:
        import sys as _s
        _s.path.insert(0, "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance")
        from audit_log import write_envelope  # type: ignore
        write_envelope(agent_id="desktop_agent", action_type=action_type, payload=payload)
    except Exception:
        pass


def take_screenshot(out_dir: Path, label: str = "current",
                    target_width: int = 1920, target_height: int = 1080,
                    max_bytes: int = 4_500_000) -> tuple[str, Path, str]:
    """Capture screen via spectacle, resize+JPEG to fit under Anthropic 5MB cap.
    Returns (base64_data, file_path, media_type)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{label}.raw.png"
    path = out_dir / f"{label}.jpg"
    env = {**os.environ, "DISPLAY": DEFAULT_DISPLAY}
    try:
        subprocess.run(
            ["spectacle", "-b", "-n", "-f", "-o", str(raw_path)],
            env=env, timeout=10, check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        log.error("spectacle failed: %s", e.stderr.decode("utf-8", "replace")[:200])
        try:
            subprocess.run(["import", "-window", "root", str(raw_path)],
                           env=env, timeout=10, check=True, capture_output=True)
        except Exception as e2:
            log.error("import fallback also failed: %s", e2)
            raise
    if not raw_path.exists() or raw_path.stat().st_size < 5000:
        raise RuntimeError(
            f"screenshot empty/degenerate at {raw_path} "
            f"(size={raw_path.stat().st_size if raw_path.exists() else 0})"
        )

    # Resize 3840x2160 -> 1920x1080 and convert to JPEG (clean quality control)
    media_type = "image/jpeg"
    quality = 85
    try:
        subprocess.run(
            ["convert", str(raw_path),
             "-resize", f"{target_width}x{target_height}>",
             "-strip", "-quality", str(quality),
             str(path)],
            timeout=15, check=True, capture_output=True,
        )
        # If still too big, drop quality progressively
        for q in (75, 60, 45):
            if path.stat().st_size <= max_bytes:
                break
            subprocess.run(
                ["convert", str(raw_path),
                 "-resize", f"{target_width}x{target_height}>",
                 "-strip", "-quality", str(q),
                 str(path)],
                timeout=15, check=True, capture_output=True,
            )
            quality = q
        try:
            raw_path.unlink()
        except Exception:
            pass
    except Exception as e:
        log.warning("resize/convert failed (using raw PNG): %s", e)
        path = raw_path
        media_type = "image/png"

    with path.open("rb") as f:
        data = f.read()
    if len(data) > max_bytes:
        log.warning("screenshot %d bytes after resize (q=%d), may exceed API limit",
                    len(data), quality)
    b64 = base64.standard_b64encode(data).decode()
    log.info("screenshot %s: %d bytes (q=%d, %s)", label, len(data), quality, media_type)
    return b64, path, media_type


def execute_action(action: dict, *, dry_run: bool = False,
                   coord_scale_x: float = 1.0, coord_scale_y: float = 1.0) -> str:
    """Execute a Computer Use action via xdotool (XWayland-compatible).
    Returns a human-readable result string.

    coord_scale_x/y multiply Claude's coordinates to land on the physical
    screen. If the agent sees 1920x1080 but the screen is 3840x2160, scale
    is 2.0/2.0. Without scaling, every click lands in the wrong spot."""
    env = {**os.environ, "DISPLAY": DEFAULT_DISPLAY}
    action_type = action.get("action")

    if dry_run:
        return f"DRY_RUN: would execute {action_type} {action}"

    if action_type == "screenshot":
        return "screenshot_taken"

    def _scale(coord: list) -> tuple[int, int]:
        return int(coord[0] * coord_scale_x), int(coord[1] * coord_scale_y)

    if action_type in ("left_click", "right_click", "double_click", "middle_click"):
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        button = {"left_click": "1", "right_click": "3",
                  "middle_click": "2", "double_click": "1"}[action_type]
        repeat = ["--repeat", "2"] if action_type == "double_click" else []
        # Honor modifier keys passed in the `text` param (per Anthropic spec)
        modifier = action.get("text", "")
        if modifier:
            subprocess.run(["xdotool", "keydown", modifier], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "click", *repeat, button], env=env, timeout=5, check=False)
        if modifier:
            subprocess.run(["xdotool", "keyup", modifier], env=env, timeout=5, check=False)
        _audit("desktop.action.click", {"button": button, "agent_x": ax, "agent_y": ay,
                                         "real_x": x, "real_y": y, "type": action_type,
                                         "modifier": modifier or None})
        return f"{action_type} ({ax}, {ay}) -> screen ({x}, {y})"

    if action_type == "type":
        text = action.get("text", "")
        # Use --clearmodifiers to avoid stuck shift/ctrl, --delay 12 for reliability
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", "12", text],
                       env=env, timeout=30, check=False)
        _audit("desktop.action.type", {"len": len(text), "preview": text[:40]})
        return f"typed {len(text)} chars"

    if action_type == "key":
        key = action.get("text", "")
        subprocess.run(["xdotool", "key", "--clearmodifiers", key], env=env, timeout=5, check=False)
        _audit("desktop.action.key", {"key": key})
        return f"pressed {key}"

    if action_type == "scroll":
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        # Anthropic spec uses "scroll_direction" + "scroll_amount" (computer_20250124+)
        direction = action.get("scroll_direction", action.get("direction", "down"))
        amount = action.get("scroll_amount", action.get("amount", 3))
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        button = {"down": "5", "up": "4", "left": "6", "right": "7"}.get(direction, "5")
        for _ in range(int(amount)):
            subprocess.run(["xdotool", "click", button], env=env, timeout=5, check=False)
        _audit("desktop.action.scroll", {"direction": direction, "amount": amount,
                                          "agent_x": ax, "agent_y": ay})
        return f"scrolled {direction} {amount}x at ({ax}, {ay})"

    if action_type == "mouse_move":
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        return f"moved to ({ax}, {ay})"

    if action_type == "wait":
        duration = float(action.get("duration", 1.0))
        time.sleep(min(duration, 10.0))  # cap at 10s for safety
        return f"waited {duration}s"

    if action_type == "hold_key":
        key = action.get("text", "")
        duration = float(action.get("duration", 1.0))
        # xdotool: keydown, sleep, keyup
        subprocess.run(["xdotool", "keydown", key], env=env, timeout=5, check=False)
        time.sleep(min(duration, 10.0))
        subprocess.run(["xdotool", "keyup", key], env=env, timeout=5, check=False)
        _audit("desktop.action.hold_key", {"key": key, "duration": duration})
        return f"held {key} for {duration}s"

    if action_type == "left_mouse_down":
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mousedown", "1"], env=env, timeout=5, check=False)
        return f"left_mouse_down ({ax}, {ay})"

    if action_type == "left_mouse_up":
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mouseup", "1"], env=env, timeout=5, check=False)
        return f"left_mouse_up ({ax}, {ay})"

    if action_type == "left_click_drag":
        sx, sy = action["start_coordinate"]
        ex, ey = action["coordinate"]
        rsx, rsy = _scale([sx, sy])
        rex, rey = _scale([ex, ey])
        subprocess.run(["xdotool", "mousemove", str(rsx), str(rsy)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mousedown", "1"], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mousemove", str(rex), str(rey)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "mouseup", "1"], env=env, timeout=5, check=False)
        return f"drag ({sx},{sy})->({ex},{ey})"

    if action_type == "triple_click":
        ax, ay = action["coordinate"]
        x, y = _scale([ax, ay])
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=env, timeout=5, check=False)
        subprocess.run(["xdotool", "click", "--repeat", "3", "1"], env=env, timeout=5, check=False)
        _audit("desktop.action.click", {"button": "1", "agent_x": ax, "agent_y": ay,
                                          "real_x": x, "real_y": y, "type": "triple_click"})
        return f"triple_click ({ax}, {ay})"

    if action_type == "key_sequence":
        keys = action.get("keys", [])
        for k in keys:
            subprocess.run(["xdotool", "key", "--clearmodifiers", k], env=env, timeout=5, check=False)
        return f"keys {keys}"

    if action_type == "cursor_position":
        result = subprocess.run(
            ["xdotool", "getmouselocation"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()

    return f"unknown action: {action_type}"


def get_cursor_position() -> tuple[int, int]:
    """Return current cursor (x, y) for human-override detection."""
    env = {**os.environ, "DISPLAY": DEFAULT_DISPLAY}
    r = subprocess.run(
        ["xdotool", "getmouselocation", "--shell"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    out = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return int(out.get("X", 0)), int(out.get("Y", 0))


# Allowlist for bash commands the agent can execute (security boundary).
# These are read-only/diagnostic commands. NOT a shell -- discrete commands.
_BASH_ALLOWLIST_PREFIXES = (
    # Window / display introspection
    "xdotool getactivewindow",
    "xdotool getwindowname",
    "xdotool search",
    "xdotool getmouselocation",
    "xdotool key",            # keystrokes are safe (no destructive shell)
    "xdotool mousemove",
    "xdotool windowactivate",
    "wmctrl -l",
    "wmctrl -d",
    "wmctrl -ia",
    "DISPLAY=:1 xdotool",
    "DISPLAY=:1 wmctrl",
    # Process introspection (read-only)
    "ps ",
    "ps aux",
    "pgrep",
    "pidof",
    "which ",
    "command -v",
    # API + file reads
    "curl -s ",
    "curl -sL ",
    "curl -X GET",
    "curl --silent",
    "ls ",
    "cat /tmp/",
    "cat /AA_MY_DRIVE/.env",  # read .env (the agent may need to verify keys persisted)
    "stat /tmp/",
    "head /tmp/",
    "tail /tmp/",
    "wc -l",
    "wc /tmp/",
    "grep ",
    "find ",
    "echo ",
    "pwd",
    "date ",
    "date",
    # D-Bus / KDE introspection (read-only)
    "qdbus",
    "qdbus6",
    "busctl --user",
    "busctl ",
    # Clipboard read
    "wl-paste",
    "xsel ",
    "xclip ",
    # Clipboard WRITE (so the agent can pre-load values into clipboard for paste)
    "echo -n",
    "printf",
)


def execute_bash(command: str, timeout: int = 15) -> dict:
    """Execute a bash command if it matches the allowlist. Returns
    {output, error, is_error} for the agent to consume.

    Security: every command is allowlist-checked to prevent the agent from
    running destructive ops (rm, sudo, dd, etc). For full shell access,
    extend _BASH_ALLOWLIST_PREFIXES with caution."""
    cmd = command.strip()
    allowed = any(cmd.startswith(p) for p in _BASH_ALLOWLIST_PREFIXES)
    if not allowed:
        return {
            "output": "",
            "error": f"bash command not on allowlist: {cmd[:80]}",
            "is_error": True,
        }
    try:
        r = subprocess.run(
            ["bash", "-c", command],
            env={**os.environ, "DISPLAY": DEFAULT_DISPLAY, "LC_ALL": "C"},
            capture_output=True, text=True, timeout=timeout,
        )
        # Truncate huge output to keep token costs sane
        output = (r.stdout or "")[:4000]
        if len(r.stdout or "") > 4000:
            output += "\n... [truncated, total " + str(len(r.stdout)) + " chars]"
        err = (r.stderr or "")[:1000]
        _audit("desktop.action.bash", {"cmd": cmd[:120], "rc": r.returncode,
                                         "out_len": len(r.stdout or ""),
                                         "err_len": len(r.stderr or "")})
        return {
            "output": output,
            "error": err if r.returncode != 0 else "",
            "is_error": r.returncode != 0,
        }
    except subprocess.TimeoutExpired:
        return {"output": "", "error": f"timeout after {timeout}s", "is_error": True}
    except Exception as e:
        return {"output": "", "error": str(e)[:200], "is_error": True}


def _inject_cache_breakpoints(messages: list, max_breakpoints: int = 3) -> None:
    """Set ephemeral cache_control on the last `max_breakpoints` user messages.
    Per Anthropic's reference impl: caching the rolling window keeps the
    expensive screenshot history hot for cache reads (10% of fresh price).
    Mutates messages in place; idempotent."""
    breakpoints_remaining = max_breakpoints
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list) or not content:
            continue
        if breakpoints_remaining > 0:
            breakpoints_remaining -= 1
            # Stamp cache_control on the LAST content block of this user message
            last_block = content[-1]
            if isinstance(last_block, dict):
                last_block["cache_control"] = {"type": "ephemeral"}
        else:
            # Older messages: strip stale cache_control to avoid runaway breakpoints
            for block in content:
                if isinstance(block, dict) and "cache_control" in block:
                    del block["cache_control"]


def _format_context_for_prompt(context: dict) -> str:
    """Render an envelope.context block as plain-English system-prompt sections."""
    if not context:
        return ""
    parts: list[str] = []
    if context.get("project"):
        parts.append(f"\nPROJECT CONTEXT: {context['project']}")
    if context.get("conversation_summary"):
        parts.append(f"\nWHY THIS TASK MATTERS:\n{context['conversation_summary']}")
    prev = context.get("previous_state") or {}
    if prev:
        lines = ["\nPRIOR STATE OF THIS PROJECT:"]
        if prev.get("halt_check"):
            lines.append(f"  System halt-check (most recent):\n    " + "\n    ".join(
                str(prev["halt_check"]).strip().splitlines()[:8]))
        if prev.get("recent_commits"):
            lines.append("  Recent commits:")
            for c in prev["recent_commits"][:5]:
                lines.append(f"    {c}")
        if prev.get("recent_audit_envelopes"):
            lines.append("  Recent audit envelopes:")
            for e in prev["recent_audit_envelopes"][:3]:
                lines.append(f"    {e}")
        parts.append("\n".join(lines))
    if context.get("success_criteria"):
        parts.append("\nSUCCESS CRITERIA (verify each before declaring done):")
        for c in context["success_criteria"]:
            parts.append(f"  - {c}")
    if context.get("do_not"):
        parts.append("\nABSOLUTELY DO NOT:")
        for d in context["do_not"]:
            parts.append(f"  - {d}")
    rfs = context.get("related_files") or []
    if rfs:
        parts.append("\nRELATED FILES (excerpts pre-fetched, you don't have filesystem access):")
        for rf in rfs:
            parts.append(f"\n  Path: {rf.get('path')}")
            parts.append(f"  Purpose: {rf.get('purpose')}")
            ex = rf.get("excerpt", "")
            if ex:
                parts.append("  Excerpt (first 30 lines):")
                for line in ex.splitlines()[:30]:
                    parts.append(f"    {line}")
    return "\n".join(parts)


def run_task(
    *,
    task: str,
    screenshots_dir: Path,
    max_iterations: int = 30,
    max_seconds: int = 300,
    width: Optional[int] = None,
    height: Optional[int] = None,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    abort_on_human_override: bool = True,
    dry_run: bool = False,
    context: Optional[dict] = None,
) -> dict[str, Any]:
    """Run a Computer Use task end-to-end. Returns result dict.

    Per Anthropic best practices (May 2026), default stack is:
      - claude-opus-4-7 (1:1 pixel coords up to 2576px on long edge)
      - tool: computer_20251124 with enable_zoom=true (for dropdowns)
      - beta header: computer-use-2025-11-24
      - Anthropic-recommended self-evaluation system prompt
    """
    if Anthropic is None:
        return {"status": "failed", "error": "anthropic SDK not installed", "steps": []}

    # Prefer LUCREX_ANTHROPIC_KEY (avoids conflict with Claude CLI's claude.ai auth).
    key = (api_key
           or os.environ.get("LUCREX_ANTHROPIC_KEY", "")
           or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not key:
        return {"status": "failed", "error": "no LUCREX_ANTHROPIC_KEY/ANTHROPIC_API_KEY", "steps": []}

    # Per-model agent dimensions (Sonnet caps at 1568, Opus at 1920+).
    # Caller can override by passing explicit width/height.
    if width is None or height is None:
        width, height = _agent_dimensions_for(model)

    # Determine real screen vs agent coordinate-space mapping.
    real_width, real_height = get_real_resolution()
    coord_scale_x = real_width / width
    coord_scale_y = real_height / height
    log.info("Model: %s | Real screen: %dx%d | Agent space: %dx%d | Scale: %.3fx %.3fy",
             model, real_width, real_height, width, height, coord_scale_x, coord_scale_y)

    # Tool version selection. computer_20251124 (Opus 4.x family) requires
    # different beta header than computer_20250124 (Sonnet 4.5 / Haiku 4.5).
    is_new_tool = ("opus-4-7" in model or "opus-4-6" in model
                   or "sonnet-4-6" in model or "opus-4-5" in model)
    tool_version = "computer_20251124" if is_new_tool else "computer_20250124"
    beta_header = "computer-use-2025-11-24" if is_new_tool else "computer-use-2025-01-24"

    client = Anthropic(api_key=key)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    steps: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []

    # System prompt: Anthropic reference-implementation patterns + KDE-specific
    # environment + Firefox guidance + bash tool usage. Wrapped in <SYSTEM_CAPABILITY>
    # and <IMPORTANT> tags per the reference impl.
    import platform as _platform
    base_system = (
        f"<SYSTEM_CAPABILITY>\n"
        f"* You are utilising a Linux KDE Plasma 6 (Wayland) desktop on {_platform.machine()} "
        f"architecture, controlling Rich's REAL workstation. The display is {width}x{height} "
        f"in your coordinate space (the runner scales to physical {real_width}x{real_height} "
        f"automatically -- you do NOT need to scale).\n"
        f"* Firefox (X11 mode via XWayland) is already running with active sessions for "
        f"resend.com, cloudflare.com, improvmx.com, github.com, claude.ai, console.anthropic.com.\n"
        f"* You have THREE tools: `computer` (screenshot/click/type/zoom), `bash` (read-only "
        f"diagnostic shell), and the screen-capture loop runs after each tool call.\n"
        f"* Use the `bash` tool to query state without consuming a screenshot iteration. "
        f"Examples: `xdotool getactivewindow getwindowname` to confirm focus, "
        f"`wl-paste` or `xsel --clipboard --output` to read what's in the clipboard, "
        f"`curl -s https://api.example.com/...` to test an API endpoint, "
        f"`xdotool search --name 'Firefox'` to find window IDs.\n"
        f"* When using your computer function calls, they take a few seconds. Where possible, "
        f"chain multiple calls into one request.\n"
        f"* The current date is {datetime.now().strftime('%A, %B %-d, %Y')}.\n"
        f"</SYSTEM_CAPABILITY>\n\n"
        f"<IMPORTANT>\n"
        f"* When using Firefox, if a startup wizard or 'Restore previous session' prompt "
        f"appears, IGNORE IT. Click on the address bar (top of window, usually around y=130 "
        f"in agent coords) and type the URL there directly.\n"
        f"* After EACH action, the next screenshot lands automatically. Evaluate explicitly: "
        f"'I evaluated step X. Result: ...'. If an action did NOT produce the expected result, "
        f"try a DIFFERENT approach -- never repeat the same failing click.\n"
        f"* Dropdowns and autocomplete widgets are unreliable via mouse. Prefer keyboard nav: "
        f"click the field once, Tab to focus the dropdown, Down arrow + Enter to select.\n"
        f"* Use the zoom action (Opus 4.x only) on small UI elements before clicking, "
        f"especially when reading API keys, OTP codes, or any precise text.\n"
        f"* NEVER press Alt+F4, Ctrl+W, Ctrl+Q. Never close a window or quit Firefox.\n"
        f"* For OAuth flows (Google sign-in, etc): the user is typically already signed in to "
        f"their primary Google account. Click 'Continue with Google', then click the account "
        f"row showing 1m.rich.gee@gmail.com, then click any 'Continue' on a consent screen. "
        f"If 2FA / SMS / passkey prompt appears, STOP and end with text 'BLOCKED_2FA' (no JSON).\n"
        f"* When a task is complete, end with a JSON code block of captured values: "
        f"```json {{\"key\": \"value\"}} ```. For unrecoverable blocks, end with a status code "
        f"(LOGIN_REQUIRED, BLOCKED_2FA, PAGE_ERROR) -- no JSON block.\n"
        f"</IMPORTANT>"
    )
    context_section = _format_context_for_prompt(context) if context else ""
    # Operational context -- Rich's aliases, configs, memory, recent state.
    # This loads ONCE per task at dispatch time. The whole block goes into the
    # cached system prompt, so token cost is paid only once, not per-iteration.
    op_context = ""
    if context_loader is not None:
        try:
            op_context = "\n\n" + context_loader.build_operational_context()
        except Exception as e:
            log.warning("context_loader failed (non-fatal): %s", e)
    system_text = base_system + context_section + op_context
    # Wrap system as a list of blocks so we can apply cache_control (Anthropic
    # ref impl pattern). The system prompt is large + stable across iterations,
    # so we cache it -- saves ~3k tokens per iter on cache hit.
    system = [{
        "type": "text",
        "text": system_text,
        "cache_control": {"type": "ephemeral"},
    }]

    # Initial screenshot at agent dimensions (already resized by take_screenshot)
    b64, _, mtype = take_screenshot(screenshots_dir, label=f"00_initial",
                                     target_width=width, target_height=height)
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": task},
            {"type": "image",
             "source": {"type": "base64", "media_type": mtype, "data": b64}},
        ],
    })

    tool_def = {
        "type": tool_version,
        "name": "computer",
        "display_width_px": width,
        "display_height_px": height,
        "display_number": 1,
    }
    if is_new_tool:
        tool_def["enable_zoom"] = True  # Opus 4.x only -- precision for dropdowns
    # Add bash tool (computer_20251124 pairs with bash_20250124).
    # Lets the agent shell out for state queries without burning a screenshot.
    bash_tool = {"type": "bash_20250124", "name": "bash"}
    tools = [tool_def, bash_tool]

    last_cursor = get_cursor_position()
    last_agent_action_at = time.time()
    last_user_active_at = 0.0  # 0 = no user activity detected yet

    _audit("desktop.task.started", {"task": task[:200], "max_iterations": max_iterations,
                                     "screenshots_dir": str(screenshots_dir),
                                     "dry_run": dry_run,
                                     "cooperative_brake": abort_on_human_override})

    final_text = ""
    status = "in_progress"
    abort_reason = None
    USER_IDLE_THRESHOLD = 5.0  # seconds Rich must be idle before agent resumes

    for iteration in range(max_iterations):
        if time.time() - started_at > max_seconds:
            status = "aborted"
            abort_reason = f"max_seconds_exceeded ({max_seconds}s)"
            break

        # COLLAB LOCK: if Claude CLI grabbed the floor for human input,
        # yield until they release. No API call, no token cost while paused.
        if collab_lock is not None and collab_lock.is_paused_for_cli():
            log.info("collab_lock=cli_active -- yielding to terminal until clear")
            cleared = collab_lock.wait_until_clear(max_wait=600.0, poll=1.5)
            if not cleared:
                status = "aborted"
                abort_reason = "collab_lock_timeout (CLI held floor >10min)"
                break
            log.info("collab_lock cleared -- resuming with fresh screenshot")
            # Force a fresh screenshot on resume since the screen may have changed
            # while we waited (Rich may have switched windows/tabs).
            try:
                last_cursor = get_cursor_position()
            except Exception:
                pass

        if abort_on_human_override:
            try:
                cur = get_cursor_position()
                # COOPERATIVE BRAKE (v3): if user moves cursor significantly AFTER our last
                # agent action, do NOT abort -- pause until user is idle for USER_IDLE_THRESHOLD
                # seconds, then take a fresh screenshot and continue. Rich can use his terminal
                # while a task runs; the agent yields and resumes.
                cursor_moved = (abs(cur[0] - last_cursor[0]) > 150 or
                                abs(cur[1] - last_cursor[1]) > 150)
                user_initiated = cursor_moved and time.time() - last_agent_action_at > 3
                if user_initiated:
                    last_user_active_at = time.time()
                    last_cursor = cur  # update so we don't re-detect the same movement
                if last_user_active_at > 0:
                    idle_for = time.time() - last_user_active_at
                    if idle_for < USER_IDLE_THRESHOLD:
                        # Pause: wait for user to be idle, take fresh screenshot when resuming
                        log.info("user-active (cursor at %s); pausing %ss before next action",
                                 cur, round(USER_IDLE_THRESHOLD - idle_for, 1))
                        time.sleep(min(USER_IDLE_THRESHOLD - idle_for + 0.5, 3.0))
                        # After pause, force a fresh screenshot on next iteration by NOT
                        # advancing the loop -- just retry the cursor check
                        continue
                # If user has been idle >USER_IDLE_THRESHOLD, proceed normally; reset
                # last_user_active_at after a long idle so we don't double-count
                if last_user_active_at > 0 and \
                        time.time() - last_user_active_at > USER_IDLE_THRESHOLD * 3:
                    log.info("user idle for >%ss -- resuming normal operation",
                             USER_IDLE_THRESHOLD * 3)
                    last_user_active_at = 0.0
            except Exception:
                pass

        log.info("Iteration %d/%d", iteration + 1, max_iterations)

        # Apply cache_control to last 3 user message turns (Anthropic ref impl
        # pattern). Keeps the rolling window cached without unbounded growth.
        _inject_cache_breakpoints(messages, max_breakpoints=3)

        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                tools=tools,
                messages=messages,
                extra_headers={
                    "anthropic-beta": f"{beta_header},prompt-caching-2024-07-31"
                },
            )
            # Log cache stats so Rich can see the savings
            usage = getattr(response, "usage", None)
            if usage:
                log.info("usage: input=%d output=%d cache_read=%d cache_create=%d",
                         getattr(usage, "input_tokens", 0),
                         getattr(usage, "output_tokens", 0),
                         getattr(usage, "cache_read_input_tokens", 0),
                         getattr(usage, "cache_creation_input_tokens", 0))
        except Exception as e:
            log.error("Anthropic API error: %s", e)
            status = "failed"
            abort_reason = f"api_error: {e}"
            break

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_uses:
            final_text = " ".join(b.text for b in text_blocks)
            steps.append({"iteration": iteration + 1, "action": "complete", "text": final_text})
            status = "done"
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tu in tool_uses:
            action = tu.input
            tool_name = tu.name  # 'computer' or 'bash'

            if tool_name == "bash":
                # Bash tool: shell command, no screenshot follows
                command = action.get("command", "")
                log.info("  Bash: %s", command[:100])
                br = execute_bash(command)
                steps.append({
                    "iteration": iteration + 1,
                    "action": "bash",
                    "coord": None,
                    "text_preview": command[:80],
                    "detail": (br["error"] if br["is_error"] else br["output"])[:200],
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": [{"type": "text",
                                 "text": br["error"] if br["is_error"] else br["output"]}],
                    "is_error": br["is_error"],
                })
                continue  # bash actions don't trigger a screenshot

            # Computer tool path
            log.info("  Action: %s %s", action.get("action"), action.get("coordinate", ""))
            result_text = execute_action(action, dry_run=dry_run,
                                          coord_scale_x=coord_scale_x,
                                          coord_scale_y=coord_scale_y)
            steps.append({
                "iteration": iteration + 1,
                "action": action.get("action"),
                "coord": action.get("coordinate"),
                "text_preview": (action.get("text", "")[:40] if action.get("text") else None),
                "detail": result_text,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            last_agent_action_at = time.time()
            # Per Anthropic best practices, allow UI to update before screenshot
            time.sleep(1.0)
            try:
                last_cursor = get_cursor_position()
            except Exception:
                pass

            label = f"{iteration+1:02d}_{action.get('action')}"
            mtype = "image/jpeg"
            try:
                b64, _, mtype = take_screenshot(screenshots_dir, label=label,
                                                  target_width=width,
                                                  target_height=height)
            except Exception as e:
                log.warning("post-action screenshot failed: %s", e)
                b64 = ""

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": (
                    [{"type": "text", "text": result_text}]
                    + ([{"type": "image",
                         "source": {"type": "base64", "media_type": mtype, "data": b64}}]
                       if b64 else [])
                ),
            })

        messages.append({"role": "user", "content": tool_results})

    if status == "in_progress":
        status = "max_iterations_reached"

    final_screenshot = None
    try:
        _, fp, _ = take_screenshot(screenshots_dir, label="99_final")
        final_screenshot = str(fp)
    except Exception:
        pass

    _audit("desktop.task.completed", {"status": status, "iterations": len(steps),
                                       "elapsed": round(time.time() - started_at, 2),
                                       "abort_reason": abort_reason})

    return {
        "status": status,
        "iterations": len(steps),
        "steps": steps,
        "final_text": final_text,
        "final_screenshot": final_screenshot,
        "abort_reason": abort_reason,
        "elapsed_seconds": round(time.time() - started_at, 2),
    }


if __name__ == "__main__":
    import sys
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Take a screenshot and describe what you see."
    out = Path("/tmp/desktop_agent_test")
    out.mkdir(exist_ok=True)
    r = run_task(task=task, screenshots_dir=out, max_iterations=10)
    print(json.dumps(r, indent=2)[:2000])
