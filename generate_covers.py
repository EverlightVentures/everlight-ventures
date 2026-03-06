import os
import requests
import time
from pathlib import Path

API_KEY = "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"
BASE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/ADVENTURES_WITH_SAM")

COVERS = {
    "1": {
        "title": "SAM'S FIRST SUPERPOWER",
        "number": "1",
        "theme": "animals, clearing in the woods, glowing book, butterflies",
        "save_dir": BASE_DIR / "Book1/images"
    },
    "2": {
        "title": "SAM'S SECOND SUPERPOWER",
        "number": "2",
        "theme": "science lab, beakers, volcano experiment, sparks and bubbles",
        "save_dir": BASE_DIR / "Book 2/images"
    },
    "4": {
        "title": "SAM'S FOURTH SUPERPOWER",
        "number": "4",
        "theme": "nature, mountain peak, glowing green crystal, forest and river",
        "save_dir": BASE_DIR / "book_4/images"
    }
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
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    if is_bw:
        full_prompt = f"Children's coloring book line art version of: {prompt}. Bold clean black outlines, white background, no color, black and white only."
    else:
        full_prompt = prompt

    data = {
        "model": "dall-e-3",
        "prompt": full_prompt,
        "n": 1,
        "size": "1024x1024"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()['data'][0]['url']
    except Exception as e:
        print(f"Error: {e}")
        return None

def download_image(url, save_path):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved: {save_path}")
    except Exception as e:
        print(f"Error downloading: {e}")

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
