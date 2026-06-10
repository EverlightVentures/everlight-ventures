"""floating_status -- always-on-top live ticker for Lucrex hive state.

Tkinter window that pins to the top-right corner of the screen, transparent
background, gold border (Everlight brand), shows:
  - Big colored dot:
      RED   = BUSY_DRIVING_PC (hands off!)
      GOLD  = ASKING_RICH (CLI needs your input)
      BLUE  = BUSY_CLOUD (managed agent processing, PC free)
      GREEN = IDLE (all runners up, nothing active)
      GREY  = DEGRADED (some service down)
  - Headline text + active task title + queue counts

Reads /tmp/lucrex_status.json every 1.5s. Auto-relaunches via systemd if
crashed. Won't steal focus -- topmost but click-through where possible.

Per Rich (2026-05-07): "I sometimes interrupt because I can't see if it's
working." This widget is the answer -- one glance tells you HANDS OFF or OK.
"""
from __future__ import annotations

import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path

STATE_PATH = Path("/tmp/lucrex_status.json")
POLL_MS = 1500

COLORS = {
    "BUSY_DRIVING_PC": "#ff4444",
    "ASKING_RICH": "#D4A843",
    "BUSY_CLOUD": "#4d8cff",
    "IDLE": "#3ca84d",
    "DEGRADED": "#888888",
    "UNKNOWN": "#444444",
}

LABELS = {
    "BUSY_DRIVING_PC": "🛑 HANDS OFF",
    "ASKING_RICH": "❓ INPUT NEEDED",
    "BUSY_CLOUD": "☁️ CLOUD AGENT",
    "IDLE": "✓ IDLE",
    "DEGRADED": "⚠ DEGRADED",
    "UNKNOWN": "? UNKNOWN",
}


class StatusWidget:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Lucrex Status")
        self.root.overrideredirect(True)            # no window decorations
        self.root.attributes("-topmost", True)      # always on top
        self.root.attributes("-alpha", 0.92)        # slight transparency
        try:
            self.root.attributes("-type", "splash")  # X11 hint -- doesn't grab focus
        except Exception:
            pass

        # Position: top-right corner, with margin
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        widget_w = 360
        widget_h = 70
        x = sw - widget_w - 24
        y = 24
        self.root.geometry(f"{widget_w}x{widget_h}+{x}+{y}")

        # Frame styling -- gold border on dark bg
        self.frame = tk.Frame(self.root, bg="#0A0A0A", bd=2, relief="solid",
                              highlightbackground="#D4A843",
                              highlightcolor="#D4A843", highlightthickness=2)
        self.frame.pack(fill="both", expand=True)

        # Big status dot (using a Label with a colored bg)
        self.dot = tk.Label(self.frame, text="●", font=("DejaVu Sans", 28, "bold"),
                             bg="#0A0A0A", fg="#888")
        self.dot.pack(side="left", padx=10, pady=4)

        # Text panel (right of dot)
        text_frame = tk.Frame(self.frame, bg="#0A0A0A")
        text_frame.pack(side="left", fill="both", expand=True, pady=4)
        self.headline_label = tk.Label(
            text_frame, text="LOADING...",
            font=("Inter", 12, "bold"), bg="#0A0A0A", fg="#D4A843",
            anchor="w", justify="left",
        )
        self.headline_label.pack(fill="x", padx=4)
        self.detail_label = tk.Label(
            text_frame, text="", font=("Inter", 9), bg="#0A0A0A",
            fg="#E8E8E8", anchor="w", justify="left", wraplength=240,
        )
        self.detail_label.pack(fill="x", padx=4)
        self.queue_label = tk.Label(
            text_frame, text="", font=("Inter", 8), bg="#0A0A0A",
            fg="#999", anchor="w", justify="left",
        )
        self.queue_label.pack(fill="x", padx=4)

        # Allow drag to reposition (in case top-right blocks something)
        for w in (self.frame, self.dot, self.headline_label,
                  self.detail_label, self.queue_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        self._drag_offset = (0, 0)
        self._tick()

    def _start_drag(self, event) -> None:
        self._drag_offset = (event.x_root - self.root.winfo_x(),
                              event.y_root - self.root.winfo_y())

    def _on_drag(self, event) -> None:
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.root.geometry(f"+{x}+{y}")

    def _tick(self) -> None:
        try:
            state = self._read_state()
        except Exception:
            state = {"headline": "UNKNOWN"}
        self._render(state)
        self.root.after(POLL_MS, self._tick)

    def _read_state(self) -> dict:
        if not STATE_PATH.exists():
            return {"headline": "UNKNOWN"}
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def _render(self, state: dict) -> None:
        headline = state.get("headline", "UNKNOWN")
        color = COLORS.get(headline, COLORS["UNKNOWN"])
        label = LABELS.get(headline, headline)

        self.dot.config(fg=color)
        self.headline_label.config(text=label, fg=color)

        # Detail line: active task title or runner status summary
        active = state.get("active_task")
        if active:
            transport = active.get("transport", "?")
            title = (active.get("title") or "")[:50]
            self.detail_label.config(text=f"[{transport}] {title}")
        elif headline == "DEGRADED":
            runners = state.get("runners", {})
            down = [k for k, v in runners.items() if not v]
            self.detail_label.config(text="DOWN: " + ", ".join(down))
        elif headline == "ASKING_RICH":
            self.detail_label.config(text="CLI awaiting your input")
        else:
            self.detail_label.config(text="all runners green")

        q = state.get("queue", {})
        self.queue_label.config(
            text=f"queue: pending={q.get('pending', 0)} "
                 f"running={q.get('in_progress', 0)} "
                 f"done={q.get('done', 0)} "
                 f"failed={q.get('failed', 0)}"
        )

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    # Wait for the state file to exist (status_indicator should write it)
    for _ in range(30):
        if STATE_PATH.exists():
            break
        time.sleep(1)
    StatusWidget().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
