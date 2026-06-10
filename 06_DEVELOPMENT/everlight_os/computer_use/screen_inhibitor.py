"""screen_inhibitor -- prevent screen idle/lock during browser-task execution.

KDE Plasma 6 Wayland blanks the wallpaper / dims the screen when idle, which
makes spectacle return 32KB bilevel (B&W) screenshots. The Computer Use agent
then navigates blind. This module acquires a power-management inhibitor for
the duration of a task, then releases it cleanly on exit.

Strategy: best-effort with three layers.
  1. KDE-native: org.freedesktop.PowerManagement.Inhibit Inhibit(reason)
  2. systemd-inhibit fallback: spawn a `systemd-inhibit sleep <max_seconds>` child
  3. Mouse-wiggle keepalive: every 60s, do a no-op cursor jiggle so the idle
     timer resets even when both inhibitors above silently fail

Pre-flight check: if screen is ALREADY locked at dispatch, refuse the task
and log reason `screen_locked_at_dispatch`. The runner caller acts on this.

Usage:
    from screen_inhibitor import ScreenInhibitor

    with ScreenInhibitor(reason="browser-task abc123", max_seconds=300) as inh:
        if inh.locked_at_start:
            return RefusedReason("screen_locked_at_dispatch")
        run_task(...)
    # inhibitor auto-released here
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("screen_inhibitor")


@dataclass
class InhibitorState:
    dbus_cookie: Optional[str] = None
    systemd_pid: Optional[int] = None
    keepalive_thread: Optional[threading.Thread] = None
    keepalive_stop: Optional[threading.Event] = None
    locked_at_start: bool = False


def _is_screen_locked() -> bool:
    """Return True if the KDE screen-locker is currently active.
    Best-effort: tries multiple D-Bus paths; returns False on any error."""
    try:
        # KDE Plasma 6 screen-locker
        r = subprocess.run(
            ["qdbus6", "org.freedesktop.ScreenSaver", "/ScreenSaver", "GetActive"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return r.stdout.strip().lower() == "true"
    except Exception:
        pass
    try:
        sid = os.environ.get("XDG_SESSION_ID", "")
        if sid:
            r = subprocess.run(
                ["loginctl", "show-session", sid, "-p", "LockedHint", "--value"],
                capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0:
                return r.stdout.strip().lower() == "yes"
    except Exception:
        pass
    return False


def _dbus_inhibit(reason: str) -> Optional[str]:
    """Acquire org.freedesktop.PowerManagement.Inhibit cookie. Returns cookie string or None."""
    try:
        r = subprocess.run(
            ["qdbus6", "org.freedesktop.PowerManagement.Inhibit",
             "/org/freedesktop/PowerManagement/Inhibit",
             "org.freedesktop.PowerManagement.Inhibit.Inhibit",
             "lucrex_runner", reason],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            cookie = r.stdout.strip()
            log.info("D-Bus inhibitor acquired: cookie=%s", cookie)
            return cookie
        log.debug("D-Bus inhibitor stderr: %s", r.stderr[:200])
    except Exception as e:
        log.debug("D-Bus inhibit failed: %s", e)
    return None


def _dbus_uninhibit(cookie: str) -> None:
    try:
        subprocess.run(
            ["qdbus6", "org.freedesktop.PowerManagement.Inhibit",
             "/org/freedesktop/PowerManagement/Inhibit",
             "org.freedesktop.PowerManagement.Inhibit.UnInhibit", cookie],
            capture_output=True, text=True, timeout=5,
        )
        log.info("D-Bus inhibitor released")
    except Exception as e:
        log.warning("D-Bus uninhibit failed (non-fatal): %s", e)


def _systemd_inhibit_fallback(max_seconds: int, reason: str) -> Optional[int]:
    """Spawn systemd-inhibit holding for max_seconds. Returns child PID or None."""
    try:
        proc = subprocess.Popen(
            ["systemd-inhibit",
             "--what=idle:sleep:handle-lid-switch",
             "--who=lucrex_runner",
             f"--why={reason}",
             "--mode=block",
             "sleep", str(max_seconds)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info("systemd-inhibit fallback PID %d for %ds", proc.pid, max_seconds)
        return proc.pid
    except Exception as e:
        log.debug("systemd-inhibit fallback failed: %s", e)
    return None


def _mouse_wiggle_keepalive(stop_event: threading.Event, interval: float = 60.0) -> None:
    """Subtle mouse-wiggle every interval seconds to defeat any idle timer the
    inhibitors above missed. Moves cursor 1px and back -- tiny enough that
    Computer Use's human-override detector (150px threshold) won't fire.
    Stops when stop_event is set."""
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
    last_jiggle = time.time()
    while not stop_event.wait(timeout=2.0):
        if time.time() - last_jiggle < interval:
            continue
        try:
            r = subprocess.run(
                ["xdotool", "getmouselocation", "--shell"],
                env=env, capture_output=True, text=True, timeout=2,
            )
            if r.returncode != 0:
                continue
            pos = {}
            for line in r.stdout.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    pos[k.strip()] = v.strip()
            x = int(pos.get("X", 100))
            y = int(pos.get("Y", 100))
            # Wiggle: +1, then back
            subprocess.run(["xdotool", "mousemove_relative", "1", "0"],
                           env=env, capture_output=True, timeout=2)
            time.sleep(0.05)
            subprocess.run(["xdotool", "mousemove_relative", "--", "-1", "0"],
                           env=env, capture_output=True, timeout=2)
            last_jiggle = time.time()
            log.debug("keepalive wiggle at (%d,%d)", x, y)
        except Exception as e:
            log.debug("keepalive wiggle error (non-fatal): %s", e)


class ScreenInhibitor:
    """Context manager that holds an idle/lock inhibitor for the duration of a task.

    On enter: detects lock state, acquires D-Bus + systemd-inhibit, starts
    mouse-wiggle keepalive. Sets locked_at_start on the state object.

    On exit: releases all three layers cleanly. Idempotent; safe on exception.
    """

    def __init__(self, *, reason: str = "browser-task", max_seconds: int = 600,
                 enable_keepalive: bool = False) -> None:
        self.reason = reason
        self.max_seconds = max(60, min(max_seconds + 30, 1800))  # clamp 60-1800
        self.enable_keepalive = enable_keepalive
        self.state = InhibitorState()

    def __enter__(self) -> InhibitorState:
        self.state.locked_at_start = _is_screen_locked()
        if self.state.locked_at_start:
            log.warning("screen is LOCKED at dispatch -- inhibitor not acquiring")
            return self.state

        self.state.dbus_cookie = _dbus_inhibit(self.reason)
        self.state.systemd_pid = _systemd_inhibit_fallback(self.max_seconds, self.reason)

        if self.enable_keepalive:
            self.state.keepalive_stop = threading.Event()
            self.state.keepalive_thread = threading.Thread(
                target=_mouse_wiggle_keepalive,
                args=(self.state.keepalive_stop,),
                daemon=True,
                name="screen_inhibitor_keepalive",
            )
            self.state.keepalive_thread.start()
        log.info("ScreenInhibitor active: dbus=%s systemd_pid=%s keepalive=%s",
                 bool(self.state.dbus_cookie), self.state.systemd_pid,
                 bool(self.state.keepalive_thread))
        return self.state

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.state.keepalive_stop is not None:
            self.state.keepalive_stop.set()
        if self.state.dbus_cookie:
            _dbus_uninhibit(self.state.dbus_cookie)
        if self.state.systemd_pid:
            try:
                os.kill(self.state.systemd_pid, 15)  # SIGTERM
                log.info("systemd-inhibit child %d terminated", self.state.systemd_pid)
            except ProcessLookupError:
                pass
            except Exception as e:
                log.warning("systemd-inhibit kill failed: %s", e)
        # Don't suppress exceptions
        return None


@contextmanager
def acquire(reason: str = "browser-task", max_seconds: int = 600,
            enable_keepalive: bool = False):
    """Functional helper: `with screen_inhibitor.acquire('reason'):`"""
    inh = ScreenInhibitor(reason=reason, max_seconds=max_seconds,
                          enable_keepalive=enable_keepalive)
    with inh as state:
        yield state


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"Holding inhibitor for {duration}s...")
    with acquire(reason="manual-test", max_seconds=duration) as state:
        if state.locked_at_start:
            print("REFUSED: screen is locked")
            sys.exit(1)
        time.sleep(duration)
    print("released")
