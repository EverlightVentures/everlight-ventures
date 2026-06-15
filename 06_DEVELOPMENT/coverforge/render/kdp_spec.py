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
