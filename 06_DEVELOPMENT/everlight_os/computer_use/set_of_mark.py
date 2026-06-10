"""set_of_mark -- visual grounding for desktop_agent.

Instead of asking the LLM "where is the Create Key button" each iteration
(brittle vision-based coords), we run a deterministic UI-element detector
ONCE per page and present the LLM a labeled screenshot: every interactive
element gets a numbered box drawn over it. The LLM picks a NUMBER ("click
[7]"), and our code maps the number back to exact coords. Same trick
browser-use uses for browsers, extended to native apps via AT-SPI.

Three detection backends, in order of preference:
  1. AT-SPI accessibility tree (Linux native, via dogtail or pyatspi if
     available). Most accurate -- gives every button/input/link with role
     + name + bounds.
  2. CDP DOM extraction (when target is a browser tab attached via CDP).
     Already covered by browser_use_runner; this module's value is for
     non-browser apps.
  3. Edge/contour CV via OpenCV (cv2). Heuristic -- finds rectangular
     regions that LOOK clickable. Last-resort.

Output: an annotated PNG + a JSON map {index: {bbox, role, name, x, y}}.
The LLM gets the PNG, picks an index, code returns the coords for the
agent's xdotool click.

Per feedback_screenshot_security.md: the annotated screenshot is treated
as sensitive and auto-deleted after use.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("set_of_mark")


def detect_via_atspi() -> Optional[list[dict]]:
    """Use AT-SPI accessibility tree. Returns list of {role, name, bbox, x, y}
    or None if AT-SPI unavailable."""
    try:
        # Try pyatspi first (the Python binding)
        import pyatspi  # type: ignore
    except ImportError:
        return None
    elements = []
    try:
        desktop = pyatspi.Registry.getDesktop(0)
        # Walk tree, find clickable elements (buttons, links, menu items, inputs)
        clickable_roles = {
            pyatspi.ROLE_PUSH_BUTTON, pyatspi.ROLE_TOGGLE_BUTTON,
            pyatspi.ROLE_LINK, pyatspi.ROLE_MENU_ITEM,
            pyatspi.ROLE_CHECK_BOX, pyatspi.ROLE_RADIO_BUTTON,
            pyatspi.ROLE_TEXT, pyatspi.ROLE_ENTRY,
            pyatspi.ROLE_COMBO_BOX, pyatspi.ROLE_LIST_ITEM,
        }
        def walk(node, depth=0):
            if depth > 12:  # safety
                return
            try:
                if node.getRole() in clickable_roles:
                    component = node.queryComponent()
                    bbox = component.getExtents(pyatspi.DESKTOP_COORDS)
                    if bbox.width > 5 and bbox.height > 5:
                        elements.append({
                            "role": str(node.getRoleName()),
                            "name": (node.name or "")[:80],
                            "bbox": [bbox.x, bbox.y, bbox.x + bbox.width,
                                     bbox.y + bbox.height],
                            "x": bbox.x + bbox.width // 2,
                            "y": bbox.y + bbox.height // 2,
                        })
            except Exception:
                pass
            for i in range(node.childCount):
                try:
                    walk(node.getChildAtIndex(i), depth + 1)
                except Exception:
                    continue
        for i in range(desktop.childCount):
            walk(desktop.getChildAtIndex(i))
        return elements
    except Exception as e:
        log.warning("AT-SPI walk failed: %s", e)
        return None


def detect_via_cv(image_path: Path) -> list[dict]:
    """Heuristic OpenCV detection. Finds rectangular regions that resemble
    buttons/inputs (filled rectangles with consistent edges). Last resort."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        log.warning("opencv-python not installed; CV detection disabled")
        return []
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Threshold to find solid regions
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        # Dilate to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        elements = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # Filter: button-shaped (wider than tall, reasonable size)
            aspect = w / max(h, 1)
            if (40 < w < 600 and 20 < h < 80
                    and 1.0 < aspect < 8.0):
                elements.append({
                    "role": "rect",
                    "name": "",
                    "bbox": [x, y, x + w, y + h],
                    "x": x + w // 2,
                    "y": y + h // 2,
                })
        # Dedupe overlapping (NMS)
        elements.sort(key=lambda e: e["x"] * 10000 + e["y"])
        kept = []
        for e in elements:
            overlap = any(
                abs(e["x"] - k["x"]) < 30 and abs(e["y"] - k["y"]) < 20
                for k in kept
            )
            if not overlap:
                kept.append(e)
        return kept[:50]  # cap at 50 per page
    except Exception as e:
        log.warning("cv detect failed: %s", e)
        return []


def annotate_image(src_path: Path, dst_path: Path,
                   elements: list[dict]) -> Path:
    """Draw numbered boxes on the screenshot. Returns dst_path."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.warning("PIL not installed; cannot annotate")
        # Fall back: copy source to dest
        import shutil
        shutil.copy(src_path, dst_path)
        return dst_path
    img = Image.open(src_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        # Try common font paths
        for fp in ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, 28)
                break
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    for i, el in enumerate(elements):
        x1, y1, x2, y2 = el["bbox"]
        # Box (gold #D4A843 -- Everlight brand)
        draw.rectangle([x1, y1, x2, y2], outline=(212, 168, 67), width=3)
        # Label (yellow background, black text, top-left of box)
        label = str(i)
        bbox = draw.textbbox((x1, y1), label, font=font)
        bg_w = bbox[2] - bbox[0] + 8
        bg_h = bbox[3] - bbox[1] + 4
        draw.rectangle([x1, y1, x1 + bg_w, y1 + bg_h],
                       fill=(212, 168, 67))
        draw.text((x1 + 4, y1 + 2), label, fill=(10, 10, 10), font=font)

    img.save(dst_path, "PNG")
    return dst_path


def build_set_of_mark(screenshot_path: Path, out_dir: Path,
                      backend: str = "auto") -> dict:
    """Run the full pipeline. Returns:
      {
        "annotated_path": Path,    # PNG with numbered boxes
        "elements": [...],          # list of detected elements
        "backend": str,             # "atspi" | "cv" | "none"
      }
    Caller is responsible for deleting annotated_path after use."""
    out_dir.mkdir(parents=True, exist_ok=True)
    annotated = out_dir / "som_annotated.png"

    elements = []
    used_backend = "none"

    if backend in ("auto", "atspi"):
        atspi_els = detect_via_atspi()
        if atspi_els:
            elements = atspi_els
            used_backend = "atspi"

    if not elements and backend in ("auto", "cv"):
        cv_els = detect_via_cv(screenshot_path)
        if cv_els:
            elements = cv_els
            used_backend = "cv"

    if not elements:
        return {"annotated_path": None, "elements": [], "backend": "none"}

    annotate_image(screenshot_path, annotated, elements)
    return {
        "annotated_path": annotated,
        "elements": elements,
        "backend": used_backend,
    }


if __name__ == "__main__":
    # Smoke test: take a screenshot, mark it, count elements, delete the file.
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--screenshot", help="Existing screenshot to annotate")
    p.add_argument("--backend", default="auto", choices=["auto", "atspi", "cv"])
    args = p.parse_args()

    if args.screenshot:
        sshot = Path(args.screenshot)
    else:
        # Take a fresh screenshot
        sshot = Path("/tmp/som_smoke_input.png")
        env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
        subprocess.run(["spectacle", "-b", "-n", "-o", str(sshot)],
                       env=env, timeout=10, check=True)

    out_dir = Path("/tmp/som_smoke_out")
    result = build_set_of_mark(sshot, out_dir, backend=args.backend)
    print(json.dumps({
        "backend": result["backend"],
        "element_count": len(result["elements"]),
        "annotated_path": str(result["annotated_path"]),
        "first_5_elements": result["elements"][:5],
    }, indent=2, default=str))

    # Per feedback_screenshot_security.md: delete the annotated image.
    # Caller normally consumes it inline; for the smoke test we delete here.
    if result.get("annotated_path"):
        try:
            Path(result["annotated_path"]).unlink()
            print(f"\n[security] deleted {result['annotated_path']}")
        except Exception:
            pass
    if not args.screenshot:
        # Smoke test owned the input too -- delete it
        try:
            sshot.unlink()
            print(f"[security] deleted {sshot}")
        except Exception:
            pass
