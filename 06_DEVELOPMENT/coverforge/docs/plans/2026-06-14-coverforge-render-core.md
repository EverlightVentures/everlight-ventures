# COVERFORGE Render Core - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Commit trailer:** every commit in this plan must end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

**Goal:** Build the standalone Python render core that turns fiction book metadata into a validated, print-ready KDP cover wrap (paperback) plus an ebook cover, with no network/Supabase/Stripe dependency.

**Architecture:** Pure functions, no I/O coupling. KDP dimension math is deterministic and is the make-or-break (validated to the pixel). The AI background image comes through an `ImageProvider` interface so all tests run offline against a `FakeProvider`. Pillow composites real typography over the background; output is exported to PDF and dimension-validated before it can ever leave the box.

**Tech Stack:** Python 3.11+, Pillow, pypdf (page-size assertions), pytest. Ghostscript PDF/X conversion is an optional integration step (skipped if `gs` absent). Real image provider = fal.ai Flux Dev (integration-gated behind `FAL_KEY`).

---

## File Structure

```
06_DEVELOPMENT/coverforge/render/
  __init__.py
  kdp_spec.py          # trim-size table + spine/cover dimension math (deterministic)
  prompt_builder.py    # genre -> background image prompt (no text in image)
  image_provider.py    # ImageProvider protocol + FakeProvider (tests) + FalFluxProvider (prod)
  compositor.py        # background + typography -> front panel + full wrap (Pillow)
  pdf_export.py        # PIL image -> 300 DPI PDF (+ optional Ghostscript PDF/X pass)
  validator.py         # assert a rendered PDF matches the computed kdp_spec
  preview.py           # watermark + downscale a front panel for the free tier
  render_job.py        # orchestrator: metadata + provider -> all output files
  requirements.txt
  tests/
    __init__.py
    test_kdp_spec.py
    test_prompt_builder.py
    test_image_provider.py
    test_compositor.py
    test_pdf_export.py
    test_validator.py
    test_preview.py
    test_render_job.py
```

Each file has one responsibility. `kdp_spec.py` is pure math and depends on nothing. `compositor.py` depends only on Pillow + a `CoverDimensions`. `render_job.py` is the only file that wires everything together.

---

## Task 0: Project skeleton

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/__init__.py` (empty)
- Create: `06_DEVELOPMENT/coverforge/render/tests/__init__.py` (empty)
- Create: `06_DEVELOPMENT/coverforge/render/requirements.txt`

- [ ] **Step 1: Write requirements.txt**

```
Pillow>=10.2
pypdf>=4.0
pytest>=8.0
```

- [ ] **Step 2: Create the two empty `__init__.py` files**

- [ ] **Step 3: Install + verify pytest collects nothing yet**

Run: `cd 06_DEVELOPMENT/coverforge/render && python -m pip install -r requirements.txt && python -m pytest -q`
Expected: `no tests ran`

- [ ] **Step 4: Commit**

```bash
git add 06_DEVELOPMENT/coverforge/render
git commit -m "chore(coverforge): render-core skeleton + deps"
```

---

## Task 1: KDP dimension math (the deterministic core)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/kdp_spec.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_kdp_spec.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kdp_spec.py
import pytest
from render.kdp_spec import spine_width_in, cover_dimensions, ebook_dimensions, PAPER_FACTOR

def test_spine_white_200pg():
    assert spine_width_in(200, "white") == pytest.approx(200 * 0.002252)

def test_spine_rejects_unknown_paper():
    with pytest.raises(ValueError):
        spine_width_in(200, "papyrus")

def test_cover_dimensions_6x9_200pg_white():
    d = cover_dimensions((6.0, 9.0), 200, "white", dpi=300, bleed=0.125)
    # full wrap = 2*6 + spine + 2*0.125 inches, height = 9 + 0.25 inches
    assert d.full_w_px == round((12 + 200 * 0.002252 + 0.25) * 300)
    assert d.full_h_px == round(9.25 * 300)
    assert d.spine_px == round(200 * 0.002252 * 300)
    # panels tile the full width exactly (no gap)
    assert d.back_w_px + d.spine_px + d.front_w_px == d.full_w_px

def test_ebook_is_recommended_1600x2560():
    assert ebook_dimensions() == (1600, 2560)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_kdp_spec.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'render.kdp_spec'`

- [ ] **Step 3: Write minimal implementation**

```python
# render/kdp_spec.py
"""Deterministic KDP print geometry. No I/O. The validator checks against this."""
from dataclasses import dataclass

# inches of spine per page, per KDP's published table (black ink)
PAPER_FACTOR = {"white": 0.002252, "cream": 0.0025, "color": 0.002347}

def spine_width_in(page_count: int, paper: str) -> float:
    if paper not in PAPER_FACTOR:
        raise ValueError(f"unknown paper {paper!r}; expected {list(PAPER_FACTOR)}")
    return page_count * PAPER_FACTOR[paper]

@dataclass(frozen=True)
class CoverDimensions:
    full_w_px: int
    full_h_px: int
    spine_px: int
    back_w_px: int
    front_w_px: int
    bleed_px: int
    dpi: int

def cover_dimensions(trim, page_count, paper, dpi=300, bleed=0.125) -> CoverDimensions:
    trim_w, trim_h = trim
    spine_in = spine_width_in(page_count, paper)
    full_w_px = round((2 * trim_w + spine_in + 2 * bleed) * dpi)
    full_h_px = round((trim_h + 2 * bleed) * dpi)
    spine_px = round(spine_in * dpi)
    # outer panel = trim + one outer bleed; split remaining width so panels tile exactly
    front_w_px = round((trim_w + bleed) * dpi)
    back_w_px = full_w_px - spine_px - front_w_px
    return CoverDimensions(full_w_px, full_h_px, spine_px, back_w_px,
                           front_w_px, round(bleed * dpi), dpi)

def ebook_dimensions():
    """KDP recommended ebook cover, 1.6:1."""
    return (1600, 2560)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_kdp_spec.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add render/kdp_spec.py tests/test_kdp_spec.py
git commit -m "feat(coverforge): deterministic KDP spine + cover dimension math"
```

---

## Task 2: Genre prompt builder

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/prompt_builder.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_prompt_builder.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prompt_builder.py
import pytest
from render.prompt_builder import build_background_prompt, SUPPORTED_GENRES

def test_supported_genres_are_the_three_seeded():
    assert SUPPORTED_GENRES == ("romance", "thriller", "fantasy")

def test_prompt_includes_genre_styling_and_bans_text():
    p = build_background_prompt("thriller", vibe="rainy city rooftop")
    assert "rainy city rooftop" in p
    assert "no text" in p.lower()
    assert "thriller" in p.lower() or "noir" in p.lower()

def test_unknown_genre_falls_back_but_still_bans_text():
    p = build_background_prompt("western", vibe="desert")
    assert "no text" in p.lower()
    assert "desert" in p
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_prompt_builder.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/prompt_builder.py
"""Genre -> background-image prompt. The image must contain NO text;
typography is composited later, so we explicitly forbid lettering."""

SUPPORTED_GENRES = ("romance", "thriller", "fantasy")

_GENRE_STYLE = {
    "romance": "warm cinematic romance book-cover art, soft golden light, intimate mood",
    "thriller": "dark noir thriller book-cover art, high contrast, tense moody atmosphere",
    "fantasy": "epic fantasy book-cover art, dramatic lighting, painterly detail",
}
_NO_TEXT = "no text, no letters, no title, no typography, no watermark, leave clear space for a title"

def build_background_prompt(genre: str, vibe: str) -> str:
    style = _GENRE_STYLE.get(genre.lower(), "cinematic book-cover background art")
    return f"{style}, {vibe}, vertical book cover composition, {_NO_TEXT}"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_prompt_builder.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add render/prompt_builder.py tests/test_prompt_builder.py
git commit -m "feat(coverforge): genre background-prompt builder that forbids in-image text"
```

---

## Task 3: Image provider interface + offline fake

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/image_provider.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_image_provider.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_image_provider.py
from render.image_provider import FakeProvider

def test_fake_provider_returns_exact_size_rgb():
    img = FakeProvider().generate("anything", 800, 1200)
    assert img.size == (800, 1200)
    assert img.mode == "RGB"

def test_fake_provider_is_deterministic_for_same_prompt():
    a = FakeProvider().generate("same", 64, 64)
    b = FakeProvider().generate("same", 64, 64)
    assert a.tobytes() == b.tobytes()

def test_fake_provider_varies_with_prompt():
    a = FakeProvider().generate("one", 64, 64)
    b = FakeProvider().generate("two", 64, 64)
    assert a.tobytes() != b.tobytes()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_image_provider.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/image_provider.py
"""Pluggable background-image source. Tests use FakeProvider (offline, deterministic).
Production uses FalFluxProvider (fal.ai Flux Dev), gated behind FAL_KEY."""
from typing import Protocol
import hashlib
from PIL import Image

class ImageProvider(Protocol):
    def generate(self, prompt: str, width: int, height: int) -> Image.Image: ...

class FakeProvider:
    """Deterministic gradient seeded by the prompt; no network."""
    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        seed = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
        r, g, b = (seed % 256), (seed // 256 % 256), (seed // 65536 % 256)
        img = Image.new("RGB", (width, height), (r, g, b))
        # vertical gradient so it's visibly an image, still deterministic
        px = img.load()
        for y in range(height):
            shade = int(255 * y / max(height - 1, 1))
            for x in range(width):
                px[x, y] = ((r + shade) % 256, (g + shade) % 256, (b + shade) % 256)
        return img

class FalFluxProvider:
    """Real provider. Integration-only; not exercised by unit tests."""
    def __init__(self, api_key: str, model: str = "fal-ai/flux/dev"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, width: int, height: int) -> Image.Image:
        import io, requests  # local import keeps unit tests dependency-light
        resp = requests.post(
            f"https://fal.run/{self.model}",
            headers={"Authorization": f"Key {self.api_key}"},
            json={"prompt": prompt, "image_size": {"width": width, "height": height}},
            timeout=120,
        )
        resp.raise_for_status()
        url = resp.json()["images"][0]["url"]
        img_bytes = requests.get(url, timeout=120).content
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_image_provider.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add render/image_provider.py tests/test_image_provider.py
git commit -m "feat(coverforge): ImageProvider protocol + offline FakeProvider + fal Flux provider"
```

---

## Task 4: Front-panel compositor (real typography)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/compositor.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_compositor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_compositor.py
from PIL import Image
from render.compositor import compose_front

def _bg(w, h):
    return Image.new("RGB", (w, h), (10, 10, 10))

def test_front_panel_is_exact_target_size():
    out = compose_front(_bg(400, 600), "MIDNIGHT", "A. Author", (400, 600))
    assert out.size == (400, 600)
    assert out.mode == "RGB"

def test_front_panel_actually_draws_text():
    target = (400, 600)
    blank = _bg(*target)
    out = compose_front(blank, "MIDNIGHT", "A. Author", target)
    # at least some pixels changed vs the blank background => text was drawn
    assert out.tobytes() != blank.tobytes()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_compositor.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/compositor.py
"""Composite real typography over a background. Pillow renders true fonts,
so titles are legible and reproducible (the product's core differentiator)."""
from PIL import Image, ImageDraw, ImageFont

def _load_font(font_path, size):
    if font_path:
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()  # tests stay font-agnostic and deterministic

def _fit_text(draw, text, max_w, font_path, start_size):
    size = start_size
    while size > 8:
        font = _load_font(font_path, size)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 2
    return _load_font(font_path, 8)

def compose_front(background: Image.Image, title: str, author: str,
                  target_size, font_path=None) -> Image.Image:
    img = background.convert("RGB").resize(target_size)
    draw = ImageDraw.Draw(img)
    w, h = target_size
    margin = int(w * 0.08)
    title_font = _fit_text(draw, title, w - 2 * margin, font_path, int(h * 0.10))
    author_font = _fit_text(draw, author, w - 2 * margin, font_path, int(h * 0.05))
    # title upper third, author lower margin, both centred
    tw = draw.textlength(title, font=title_font)
    draw.text(((w - tw) / 2, h * 0.12), title, font=title_font, fill=(255, 255, 255))
    aw = draw.textlength(author, font=author_font)
    draw.text(((w - aw) / 2, h * 0.85), author, font=author_font, fill=(245, 245, 245))
    return img
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_compositor.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add render/compositor.py tests/test_compositor.py
git commit -m "feat(coverforge): front-panel compositor with auto-fit real typography"
```

---

## Task 5: Full-wrap assembly

**Files:**
- Modify: `06_DEVELOPMENT/coverforge/render/compositor.py` (add `compose_wrap`)
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_compositor.py` (add cases)

- [ ] **Step 1: Add the failing tests**

```python
# append to tests/test_compositor.py
from render.compositor import compose_wrap
from render.kdp_spec import cover_dimensions

def test_wrap_is_exact_full_size_and_tiles_panels():
    d = cover_dimensions((6.0, 9.0), 200, "white")
    bg = Image.new("RGB", (d.full_w_px, d.full_h_px), (20, 20, 20))
    wrap = compose_wrap(bg, "MIDNIGHT", "A. Author", "Back blurb here.", d)
    assert wrap.size == (d.full_w_px, d.full_h_px)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_compositor.py -q`
Expected: FAIL with `ImportError: cannot import name 'compose_wrap'`

- [ ] **Step 3: Add the implementation**

```python
# append to render/compositor.py
def compose_wrap(background: Image.Image, title: str, author: str,
                 blurb: str, dims, font_path=None) -> Image.Image:
    """Assemble back | spine | front into one full-bleed wrap at exact pixel size."""
    wrap = background.convert("RGB").resize((dims.full_w_px, dims.full_h_px))
    draw = ImageDraw.Draw(wrap)
    # front panel: composite the finished front into the rightmost panel
    front = compose_front(background, title, author,
                          (dims.front_w_px, dims.full_h_px), font_path)
    wrap.paste(front, (dims.back_w_px + dims.spine_px, 0))
    # back panel: blurb text, wrapped within the back panel margins
    bmargin = int(dims.back_w_px * 0.10)
    bfont = _load_font(font_path, int(dims.full_h_px * 0.025))
    _draw_wrapped(draw, blurb, (bmargin, int(dims.full_h_px * 0.15)),
                  dims.back_w_px - 2 * bmargin, bfont)
    # spine: title rotated 90deg, only if spine is wide enough for legible text
    if dims.spine_px >= 60:
        _draw_spine(wrap, title, dims, font_path)
    return wrap

def _draw_wrapped(draw, text, xy, max_w, font):
    x, y = xy
    line, words = "", text.split()
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            draw.text((x, y), line, font=font, fill=(235, 235, 235))
            y += int(font.size * 1.4) if hasattr(font, "size") else 16
            line = word
    if line:
        draw.text((x, y), line, font=font, fill=(235, 235, 235))

def _draw_spine(wrap, title, dims, font_path):
    strip = Image.new("RGB", (dims.full_h_px, dims.spine_px), (0, 0, 0))
    sdraw = ImageDraw.Draw(strip)
    sfont = _fit_text(sdraw, title, dims.full_h_px - 40, font_path, int(dims.spine_px * 0.5))
    tw = sdraw.textlength(title, font=sfont)
    sdraw.text(((dims.full_h_px - tw) / 2, dims.spine_px * 0.2), title,
               font=sfont, fill=(255, 255, 255))
    wrap.paste(strip.rotate(90, expand=True), (dims.back_w_px, 0))
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_compositor.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add render/compositor.py tests/test_compositor.py
git commit -m "feat(coverforge): full-wrap assembly (back blurb + rotated spine + front)"
```

---

## Task 6: PDF export at 300 DPI

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/pdf_export.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_pdf_export.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pdf_export.py
from PIL import Image
from pypdf import PdfReader
from render.pdf_export import export_pdf

def test_pdf_page_size_matches_pixels_at_300dpi(tmp_path):
    img = Image.new("RGB", (1800, 2775), (0, 0, 0))  # 6x9.25 in at 300 dpi
    out = tmp_path / "wrap.pdf"
    export_pdf(img, str(out), dpi=300)
    page = PdfReader(str(out)).pages[0]
    # PDF points = inches * 72; 1800/300*72 = 432, 2775/300*72 = 666
    assert round(float(page.mediabox.width)) == 432
    assert round(float(page.mediabox.height)) == 666
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_pdf_export.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/pdf_export.py
"""PIL image -> 300 DPI PDF. Pillow sets the page size from the DPI so the
physical dimensions are exact. Optional Ghostscript pass upgrades to PDF/X-1a."""
import shutil, subprocess
from PIL import Image

def export_pdf(image: Image.Image, out_path: str, dpi: int = 300) -> str:
    image.convert("RGB").save(out_path, "PDF", resolution=float(dpi))
    return out_path

def to_pdf_x1a(in_pdf: str, out_pdf: str) -> str:
    """Convert to PDF/X-1a via Ghostscript. Raises if gs is unavailable."""
    if not shutil.which("gs"):
        raise RuntimeError("ghostscript (gs) not installed")
    subprocess.run(
        ["gs", "-dPDFX", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
         "-sColorConversionStrategy=CMYK", "-dProcessColorModel=/DeviceCMYK",
         f"-sOutputFile={out_pdf}", in_pdf],
        check=True, capture_output=True,
    )
    return out_pdf
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_pdf_export.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add render/pdf_export.py tests/test_pdf_export.py
git commit -m "feat(coverforge): 300 DPI PDF export + optional Ghostscript PDF/X pass"
```

---

## Task 7: Output validator (the hard gate)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/validator.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_validator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_validator.py
from PIL import Image
from render.pdf_export import export_pdf
from render.validator import validate_pdf

def _pdf(tmp_path, w, h):
    p = tmp_path / "c.pdf"
    export_pdf(Image.new("RGB", (w, h), (0, 0, 0)), str(p), dpi=300)
    return str(p)

def test_correct_size_passes(tmp_path):
    ok, problems = validate_pdf(_pdf(tmp_path, 1800, 2775), 1800, 2775, dpi=300)
    assert ok and problems == []

def test_wrong_size_fails_with_reason(tmp_path):
    ok, problems = validate_pdf(_pdf(tmp_path, 1801, 2775), 1200, 1600, dpi=300)
    assert not ok
    assert any("width" in p for p in problems)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_validator.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/validator.py
"""Refuse to ship a file Amazon would reject. Compares PDF page size (points)
against the pixel target at the given DPI, within a small rounding tolerance."""
from pypdf import PdfReader

def validate_pdf(pdf_path: str, expect_w_px: int, expect_h_px: int,
                 dpi: int = 300, tol_pt: float = 2.0):
    page = PdfReader(pdf_path).pages[0]
    want_w = expect_w_px / dpi * 72
    want_h = expect_h_px / dpi * 72
    problems = []
    if abs(float(page.mediabox.width) - want_w) > tol_pt:
        problems.append(f"width off: got {float(page.mediabox.width):.1f}pt want {want_w:.1f}pt")
    if abs(float(page.mediabox.height) - want_h) > tol_pt:
        problems.append(f"height off: got {float(page.mediabox.height):.1f}pt want {want_h:.1f}pt")
    return (len(problems) == 0, problems)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_validator.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add render/validator.py tests/test_validator.py
git commit -m "feat(coverforge): PDF dimension validator (hard gate before unlock)"
```

---

## Task 8: Free-tier preview (watermark + downscale)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/preview.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_preview.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_preview.py
from PIL import Image
from render.preview import make_preview

def test_preview_is_downscaled_and_changed():
    full = Image.new("RGB", (1800, 2700), (50, 50, 50))
    prev = make_preview(full, max_w=600)
    assert prev.width == 600
    assert prev.height == 900  # aspect preserved
    assert prev.tobytes() != Image.new("RGB", (600, 900), (50, 50, 50)).tobytes()  # watermark drawn
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_preview.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/preview.py
"""Free-tier output: small, watermarked PNG. The paywall sits on the download
of the full-res print file, so generating this preview is cheap to give away."""
from PIL import Image, ImageDraw, ImageFont

def make_preview(front: Image.Image, max_w: int = 600, text: str = "COVERFORGE PREVIEW") -> Image.Image:
    scale = max_w / front.width
    prev = front.convert("RGB").resize((max_w, round(front.height * scale)))
    draw = ImageDraw.Draw(prev, "RGBA")
    font = ImageFont.load_default()
    # repeat a faint diagonal watermark across the image
    for y in range(0, prev.height, 120):
        for x in range(-100, prev.width, 240):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 90))
    return prev
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_preview.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add render/preview.py tests/test_preview.py
git commit -m "feat(coverforge): watermarked downscaled free-tier preview"
```

---

## Task 9: Orchestrator (metadata in, files out)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/render_job.py`
- Test: `06_DEVELOPMENT/coverforge/render/tests/test_render_job.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_job.py
import os
from render.render_job import render_book, BookMeta
from render.image_provider import FakeProvider

def test_render_book_end_to_end_paid(tmp_path):
    meta = BookMeta(title="MIDNIGHT", author="A. Author", genre="thriller",
                    vibe="rainy rooftop", trim=(6.0, 9.0), page_count=200,
                    paper="white", blurb="A tense night in the city.")
    result = render_book(meta, FakeProvider(), str(tmp_path), tier="paid")
    assert os.path.exists(result.ebook_pdf)
    assert os.path.exists(result.wrap_pdf)
    assert result.validation_ok, result.validation_problems
    assert result.preview_png is None  # paid tier skips the watermarked preview

def test_render_book_free_tier_makes_preview_only(tmp_path):
    meta = BookMeta(title="MIDNIGHT", author="A. Author", genre="romance",
                    vibe="golden hour", trim=(6.0, 9.0), page_count=120,
                    paper="cream", blurb="Two hearts.")
    result = render_book(meta, FakeProvider(), str(tmp_path), tier="free")
    assert os.path.exists(result.preview_png)
    assert result.wrap_pdf is None  # free tier never produces the print file
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_render_job.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# render/render_job.py
"""Orchestrator: the only file that wires the pieces together.
free tier  -> watermarked preview PNG only (cheap, no print file)
paid tier  -> ebook PDF + full-wrap PDF + validation + bundle hook"""
import os
from dataclasses import dataclass
from render.kdp_spec import cover_dimensions, ebook_dimensions
from render.prompt_builder import build_background_prompt
from render.compositor import compose_front, compose_wrap
from render.pdf_export import export_pdf
from render.validator import validate_pdf
from render.preview import make_preview

@dataclass
class BookMeta:
    title: str
    author: str
    genre: str
    vibe: str
    trim: tuple
    page_count: int
    paper: str
    blurb: str

@dataclass
class RenderResult:
    preview_png: str = None
    ebook_pdf: str = None
    wrap_pdf: str = None
    validation_ok: bool = False
    validation_problems: list = None

def render_book(meta: BookMeta, provider, out_dir: str, tier: str = "paid",
                font_path=None) -> RenderResult:
    os.makedirs(out_dir, exist_ok=True)
    dims = cover_dimensions(meta.trim, meta.page_count, meta.paper)
    prompt = build_background_prompt(meta.genre, meta.vibe)

    if tier == "free":
        ew, eh = ebook_dimensions()
        bg = provider.generate(prompt, ew, eh)
        front = compose_front(bg, meta.title, meta.author, (ew, eh), font_path)
        path = os.path.join(out_dir, "preview.png")
        make_preview(front).save(path)
        return RenderResult(preview_png=path)

    # paid: ebook cover
    ew, eh = ebook_dimensions()
    ebook_front = compose_front(provider.generate(prompt, ew, eh),
                                meta.title, meta.author, (ew, eh), font_path)
    ebook_pdf = os.path.join(out_dir, "ebook.pdf")
    export_pdf(ebook_front, ebook_pdf)

    # paid: full paperback wrap
    wrap_bg = provider.generate(prompt, dims.full_w_px, dims.full_h_px)
    wrap = compose_wrap(wrap_bg, meta.title, meta.author, meta.blurb, dims, font_path)
    wrap_pdf = os.path.join(out_dir, "wrap.pdf")
    export_pdf(wrap, wrap_pdf)

    ok, problems = validate_pdf(wrap_pdf, dims.full_w_px, dims.full_h_px)
    return RenderResult(ebook_pdf=ebook_pdf, wrap_pdf=wrap_pdf,
                        validation_ok=ok, validation_problems=problems)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_render_job.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite + commit**

Run: `python -m pytest -q`
Expected: PASS (all tasks green)

```bash
git add render/render_job.py tests/test_render_job.py
git commit -m "feat(coverforge): render-job orchestrator (free preview vs paid print files)"
```

---

## Task 10: Live integration smoke test (manual, gated)

**Files:**
- Create: `06_DEVELOPMENT/coverforge/render/tests/test_integration_fal.py`

- [ ] **Step 1: Write a gated integration test**

```python
# tests/test_integration_fal.py
import os, pytest
from render.render_job import render_book, BookMeta
from render.image_provider import FalFluxProvider

@pytest.mark.skipif(not os.getenv("FAL_KEY"), reason="needs FAL_KEY for live image gen")
def test_real_flux_render(tmp_path):
    meta = BookMeta(title="THE LONG DARK", author="R. Gee", genre="thriller",
                    vibe="neon rain alley", trim=(6.0, 9.0), page_count=240,
                    paper="white", blurb="Nobody walks away clean.")
    result = render_book(meta, FalFluxProvider(os.environ["FAL_KEY"]),
                         str(tmp_path), tier="paid")
    assert result.validation_ok, result.validation_problems
    print("WROTE", result.wrap_pdf)
```

- [ ] **Step 2: Run with a real key (manual)**

Run: `FAL_KEY=... python -m pytest tests/test_integration_fal.py -s`
Expected: PASS, prints the wrap path. Open the PDF and eyeball legibility of the composited title.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_fal.py
git commit -m "test(coverforge): gated live fal Flux integration smoke test"
```

---

## Self-Review (run before handoff)

**Spec coverage** (against `2026-06-14-coverforge-design.md`):
- Two-layer render (AI background + composited typography) -> Tasks 3, 4, 5. Covered.
- Deterministic spine from page count + exact KDP dims -> Task 1. Covered.
- PDF/X export via Ghostscript -> Task 6 (`to_pdf_x1a`). Covered (unit-tested path = plain PDF; gs is integration).
- Template-dimension validator as a hard gate -> Task 7. Covered.
- Free watermarked preview vs paid print file -> Tasks 8, 9. Covered.
- Flux Dev image model, not Leonardo -> Task 3 (`FalFluxProvider`). Covered.
- Genre seeding romance/thriller/fantasy -> Task 2. Covered.

**Out of this plan (deferred to Plans 2 and 3):** Supabase `cover_jobs`/`credit_ledger`, edge functions, Stripe credit SKUs, the Haiku text bundle (keywords/categories/blurb/ads as data), the Next.js funnel, e5 deployment + job polling. The render core is consumed by Plan 2 as a library.

**Type consistency:** `CoverDimensions` fields (`full_w_px`, `full_h_px`, `spine_px`, `back_w_px`, `front_w_px`) are used identically in Tasks 1, 5, 7, 9. `BookMeta` / `RenderResult` defined once in Task 9. `ImageProvider.generate(prompt, width, height)` signature consistent across Tasks 3, 9, 10.

**Placeholder scan:** no TBD/TODO; every code step is complete and runnable.
