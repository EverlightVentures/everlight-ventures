import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from shared.publishing.book_config import BOOKS as BOOK_REGISTRY
from shared.publishing.openai_images import generate_image as _shared_generate, download_image as _shared_download

API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Cover themes per book (generate_covers.py uses a different BASE_DIR -- legacy KDP path)
_LEGACY_BASE = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/ADVENTURES_WITH_SAM")
COVERS = {
    "1": {
        "title": "SAM'S FIRST SUPERPOWER",
        "number": "1",
        "theme": "animals, clearing in the woods, glowing book, butterflies",
        "save_dir": BOOK_REGISTRY[1]["img_dir"],
    },
    "2": {
        "title": "SAM'S SECOND SUPERPOWER",
        "number": "2",
        "theme": "science lab, beakers, volcano experiment, sparks and bubbles",
        "save_dir": BOOK_REGISTRY[2]["img_dir"],
    },
    "4": {
        "title": "SAM'S FOURTH SUPERPOWER",
        "number": "4",
        "theme": "nature, mountain peak, glowing green crystal, forest and river",
        "save_dir": BOOK_REGISTRY[4]["img_dir"],
    },
}

STYLE_GUIDE = """
STYLE: High-quality 3D digital animation style, Disney/Pixar aesthetic, cinematic lighting, vibrant saturated colors.
COMPOSITION: 
- Title 'TITLE_TEXT' in bold white curved font at the top.
- Sam (6yo boy, messy brown hair, big brown eyes) in the center, heroic pose, wearing an orange/yellow shirt with a glowing circular blue emblem on his chest showing the number 'BOOK_NUM'.
- Robo (friendly rounded silver robot companion) to his right with glowing LED eyes.
- Sam wears a red cape.
- Background: THEME_TEXT.
- High energy, magical glowing particles.
"""

def generate_image(prompt, is_bw=False):
    """Generate image via shared utility."""
    return _shared_generate(
        prompt,
        is_bw=is_bw,
        bw_prefix="Children's coloring book line art version of: ",
        style_suffix="Bold clean black outlines, white background, no color, black and white only." if is_bw else "",
        api_key=API_KEY,
    )


def download_image(url, save_path):
    """Download image via shared utility."""
    _shared_download(url, save_path)

if __name__ == "__main__":
    for bid, info in COVERS.items():
        print(f"--- Generating Cover for Book {bid} ---")
        prompt = STYLE_GUIDE.replace("TITLE_TEXT", info["title"]).replace("BOOK_NUM", info["number"]).replace("THEME_TEXT", info["theme"])
        
        # Color Cover
        color_path = info["save_dir"] / f"{bid}_cover.jpg"
        if not color_path.exists():
            url = generate_image(prompt)
            if url: download_image(url, color_path)
            time.sleep(2)
            
        # B&W Cover
        bw_path = info["save_dir"] / f"{bid}_cover_bw.jpg"
        if not bw_path.exists():
            url = generate_image(prompt, is_bw=True)
            if url: download_image(url, bw_path)
            time.sleep(2)
