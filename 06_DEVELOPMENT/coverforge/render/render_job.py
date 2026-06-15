# render/render_job.py
"""Orchestrator: the only file that wires the pieces together.
free tier  -> watermarked preview PNG only (cheap, no print file)
paid tier  -> ebook PDF + full-wrap PDF + validation + bundle hook"""
import os
from dataclasses import dataclass, field
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
    validation_problems: list = field(default_factory=list)

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
