# render/produce.py
"""Top-level: one book's metadata -> all assets. Free tier = preview only;
paid tier = print files + listing bundle."""
from dataclasses import dataclass
from render.render_job import render_book, RenderResult
from render.bundle import generate_bundle, Bundle


@dataclass
class Assets:
    render: RenderResult
    bundle: Bundle = None


def produce_assets(meta, image_provider, llm, out_dir: str, tier: str = "paid", font_path=None) -> Assets:
    render = render_book(meta, image_provider, out_dir, tier=tier, font_path=font_path)
    if tier == "paid":
        return Assets(render=render, bundle=generate_bundle(meta, llm))
    return Assets(render=render, bundle=None)
