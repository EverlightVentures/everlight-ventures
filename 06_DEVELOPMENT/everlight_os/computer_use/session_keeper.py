"""session_keeper -- one-time per-workshift permission acquisition.

Rich's frustration: KDE Plasma 6 Wayland prompts for "remote control privileges"
every time the desktop_runner starts a task, because xdotool injects synthetic
mouse/key events through XWayland which Plasma flags as remote-control. Even
with the inhibitor's keepalive wiggle disabled (now default), each new
desktop_agent run that calls xdotool can re-trigger the prompt.

This keeper runs ONCE at the start of a workshift. It:
  1. Acquires a long-lived screen-power inhibitor (8 hours).
  2. Triggers the xdg-desktop-portal-kde "RemoteDesktop" permission flow ONCE
     (Rich clicks 'Remember' / 'This session').
  3. Holds an idle session in a quiet loop so the permission stays warm.
  4. Releases on Ctrl+C / SIGTERM / shift-end.

Usage at start of workshift:
    python3 session_keeper.py --hours 8 &

Then desktop_runner tasks during the day inherit the warm permission.

To stop: Ctrl+C or `pkill -f session_keeper.py`.
"""
from __future__ import annotations

import argparse
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from screen_inhibitor import ScreenInhibitor

log = logging.getLogger("session_keeper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_running = True


def _stop(signum, frame):
    global _running
    log.info("signal %d received; releasing session", signum)
    _running = False


def _warm_xdotool_permission() -> None:
    """Issue ONE harmless xdotool event so KDE Plasma prompts for the
    'allow remote control' permission ONCE. Rich clicks 'Allow this session'
    or 'Remember' and the permission warms up for the workshift."""
    try:
        # A no-op cursor query is the lightest way to trigger the input layer
        # without actually moving the mouse.
        subprocess.run(["xdotool", "getmouselocation"],
                       capture_output=True, timeout=5)
        log.info("xdotool warmed -- if KDE prompted, click 'Allow' once")
    except Exception as e:
        log.warning("xdotool warm failed (non-fatal): %s", e)


def _keep_bt_mouse_alive() -> None:
    """Disable USB autosuspend on the Realtek BT radio so Rich's mouse stays
    connected during long agent tasks. Needs sudo. Uses pwsudo (Rich's armed
    non-prompting sudo wrapper) so this doesn't block the keeper.

    Source script:
        /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/keep_bt_mouse_alive.sh
    """
    script = Path("/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/keep_bt_mouse_alive.sh")
    if not script.exists():
        log.info("keep_bt_mouse_alive.sh not found at %s -- skipping", script)
        return
    pwsudo = Path.home() / "bin" / "pwsudo"
    sudo_cmd = str(pwsudo) if pwsudo.exists() else "sudo"
    try:
        r = subprocess.run([sudo_cmd, "bash", str(script)],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            log.info("BT mouse keep-alive applied: %s", r.stdout.strip().splitlines()[-1] if r.stdout else "ok")
        else:
            log.warning("BT keep-alive returned %d: %s", r.returncode, r.stderr.strip()[:200])
    except subprocess.TimeoutExpired:
        log.warning("BT keep-alive timed out -- check pwsudo / sudoers config")
    except Exception as e:
        log.warning("BT keep-alive failed (non-fatal): %s", e)


def main() -> int:
    p = argparse.ArgumentParser(description="Hold workshift session permissions")
    p.add_argument("--hours", type=float, default=8.0,
                   help="How many hours to keep alive (default 8)")
    args = p.parse_args()

    duration_seconds = int(args.hours * 3600)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    log.info("session_keeper starting -- holding for %.1f hours", args.hours)
    log.info("if KDE prompts for 'remote control' approve ONCE with 'Allow this session'")

    started = time.time()
    with ScreenInhibitor(reason="lucrex-workshift",
                          max_seconds=duration_seconds,
                          enable_keepalive=False) as state:
        if state.locked_at_start:
            log.error("screen is locked; unlock and re-run")
            return 1
        log.info("inhibitor acquired: dbus=%s systemd_pid=%s",
                 bool(state.dbus_cookie), state.systemd_pid)

        # Warm the permission
        _warm_xdotool_permission()
        # Disable BT USB autosuspend so the Bluetooth mouse doesn't disconnect
        _keep_bt_mouse_alive()
        log.info("session keeper running. Press Ctrl+C to release.")

        # Quiet loop -- no input events, just inhibitor active
        while _running:
            time.sleep(15)
            elapsed = time.time() - started
            if elapsed > duration_seconds:
                log.info("workshift duration reached (%.1fh)", args.hours)
                break

    log.info("session_keeper exited cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
