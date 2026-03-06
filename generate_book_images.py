import os
import re
import requests
import json
from pathlib import Path
import time

# Configuration
API_KEY = "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"
BASE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Publishing/Ebook_Sells/Adventures_Series/ADVENTURES_WITH_SAM")

BOOKS = {
    "1": {
        "manuscript": BASE_DIR / "Book1/Sams_First_Superpower_MASTER.md",
        "image_dir": BASE_DIR / "Book1/images",
        "prefix": "1_"
    },
    "2": {
        "manuscript": BASE_DIR / "Book 2/Sams_Second_Superpower_MASTER.md",
        "image_dir": BASE_DIR / "Book 2/images",
        "prefix": "2_"
    },
    "4": {
        "manuscript": BASE_DIR / "book_4/manuscript/Sams_Fourth_Superpower_MASTER.md",
        "image_dir": BASE_DIR / "book_4/images",
        "prefix": "4_"
    },
    "5": {
        "manuscript": BASE_DIR / "book_5/manuscript/Sams_Fifth_Superpower_MASTER.md",
        "image_dir": BASE_DIR / "book_5/images",
        "prefix": "5_",
        "prompts_file": BASE_DIR / "book_5/ILLUSTRATION_BRIEF.md"
    }
}

# Enhanced Style Guide for consistent 3D Animation look
STYLE_GUIDE = """
STYLE: 3D digital animation style, high-quality, Disney/Pixar aesthetic, cinematic lighting, vibrant and saturated colors.
CHARACTERS:
- Sam: 6-7 years old boy, messy spiky brown hair, large expressive brown eyes, energetic posture, wearing a red t-shirt.
- Robo: Friendly rounded silver/white robot companion, compact size, big glowing blue LED eyes, chest display screen with simple icons.

BOOK 5 ADDITIONAL CHARACTERS:
- Ms. Reyes: Tall woman, kind dark eyes, clipboard in hand, warm professional, community center director.
- Mia: Young girl (~5-6), two braids, paint on her fingers, bright creative expression.
- Oliver: Young boy (~5-6), round glasses, neat appearance, holds a notebook.
- Danny: Small quiet boy (~5-6), gentle demeanor, soft eyes.
- Priya: Young girl (~5-6), dark hair, bright curious eyes, carries a journal.
- Jax: Boy (~5-6), slightly tough exterior, but eyes that show hidden vulnerability.
- Grandma: Elderly woman, silver-white hair in a braid, dark warm eyes like Sam's, simple blue dress.
"""

# Custom prompts for Book 5 (manuscript uses inline image refs, not description blocks)
BOOK5_PROMPTS = {
    1: "Sam, a 6-7 year old boy with messy spiky brown hair and red t-shirt, sitting on the front steps of a brick community center building with his compact silver robot companion Robo beside him. Warm Saturday morning, wide lawn with picnic tables, basketball court, bulletin board with flyers.",
    2: "Inside a bright community center room with tables, chairs, crayons, and scattered books. Sam sits cross-legged on the floor at eye-level with five young kids in a loose circle: Mia with two braids and paint on fingers, Oliver with glasses, small Danny hugging his knees, Priya looking at the floor, and Jax with crossed arms. Robo displays a smiley face. Ms. Reyes stands in the doorway.",
    3: "Sam leading five young kids on an outdoor adventure in a big park with old trees lining a path. Danny holds up his backpack excitedly, Mia points at sunlight breaking through clouds, Priya tugs her raincoat, Oliver watches a butterfly, Jax points at a playground. Robo's chest display shows a running tally count.",
    4: "Sam and five kids building a birdhouse together in an open meadow between three tall oak trees. Robo projects a blueprint onto a flat rock. Oliver measures with a ruler, Mia fits wooden pieces together, Danny holds boards steady, Priya examines a hole size, Jax inspects everything carefully. Supplies scattered around: small boards, screws, twine.",
    5: "Sam and six kids standing at the edge of a very overgrown community garden. Raised garden beds falling apart, weeds everywhere, fence with holes. The kids look overwhelmed but Sam stands determined with a confident expression. A damaged garden with visible potential underneath the neglect.",
    6: "Epic split-action scene of Sam using all superpowers to restore a community garden. Sam kneeling and talking to rabbits, analyzing soil, listening to a fence post, palms pressed to the earth with eyes closed. Around him, five young kids working: pulling weeds, fixing fence sections, spreading dark compost, planting seeds in raised beds. Garden mid-transformation from overgrown to beautiful.",
    7: "A beautifully restored community garden in full bloom. Red tomatoes, tall golden sunflowers, green herbs. A professional woman inspector walking through looking impressed. Five kids cheering in celebration. Painted colorful signs on garden beds, a creative rain collection system visible. Ms. Reyes smiling proudly.",
    8: "Warm intimate scene showing five kids each with their discovered talent in a community center. Mia painting colorful signs, Oliver sketching in a notebook, Danny with stray cats curled beside him, Priya presenting a growth journal, and Jax sitting in a corner reading his first book with shining eyes. Sam watches from across the room with pride.",
    9: "Sam and his silver robot companion Robo walking through a park path at golden sunset. Beautiful warm orange and purple lighting. Sam looks contemplative and emotionally moved. Robo's display shows the word 'proud.' Trees silhouetted against the sky, path stretching ahead. A quiet, reflective moment.",
    10: "Grand outdoor celebration at a thriving community garden. Tables with lemonade and cookies, families gathered. Multiple adult characters present: a man in a recycling cap, a farmer with apple crate, a ranger woman with saplings, a scientist in a lab coat. Center stage: a young boy reading a book out loud to the entire crowd while his mother cries happy tears.",
    11: "Emotionally powerful reunion scene. Sam turning around with surprise to see his grandmother -- an elderly woman with silver-white hair in a braid, dark warm eyes, simple blue dress, holding a basket. Sam running to embrace her. Garden celebration softly blurred in background. Warm golden afternoon light.",
    12: "Epic magical series finale. Sam holding a glowing golden book with five blazing star symbols on the cover. Golden light flowing through Sam and radiating outward. Animals gathering around him: a cat, rabbit, puppy, bird on his shoulder. Five young kids watching in awe. An elderly grandmother with silver braid standing behind Sam with hand on his shoulder. Robot companion displaying a heart. Lush garden setting, magical golden light illuminating everything.",
    "cover": "Children's book cover for 'Sam's Fifth Superpower'. Sam standing confidently at center, five young kids of diverse backgrounds arranged behind him in an arc, compact silver robot beside him. Community garden in full bloom as backdrop. An open golden book in Sam's hands with five glowing star symbols and light streaming upward. Title space at top. 3D Disney/Pixar animation style, vibrant, epic, cinematic lighting."
}

def generate_image(prompt, is_bw=False):
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    if is_bw:
        # Instruction for coloring book style
        full_prompt = f"Professional children's coloring book line art, thick bold clean black outlines, white background, no color, black and white only, gentle grey shading for depth. Scene: {prompt}. {STYLE_GUIDE}"
    else:
        full_prompt = f"Vibrant 3D animation style children's book illustration, cinematic lighting, rich textures, soft depth of field. Scene: {prompt}. {STYLE_GUIDE}"

    data = {
        "model": "dall-e-3",
        "prompt": full_prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "standard"
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        return response.json()['data'][0]['url']
    except Exception as e:
        print(f"Error generating: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Details: {e.response.text}")
        return None

def download_image(url, save_path):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Successfully saved to {save_path}")
        return True
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

def process_book(book_id):
    config = BOOKS[book_id]
    manuscript_path = config["manuscript"]
    image_dir = config["image_dir"]
    prefix = config["prefix"]
    
    image_dir.mkdir(parents=True, exist_ok=True)
    
    with open(manuscript_path, 'r') as f:
        content = f.read()

    # Regex for illustration blocks: **[LABEL]**\n*Description*
    # Using re.DOTALL to capture multi-line descriptions if they exist
    pattern = r"\*\*\[(LEFT PAGE -- B&W COLORING ILLUSTRATION|RIGHT PAGE -- FULL COLOR ILLUSTRATION)\]\*\*\s*\n\*(.*?)\*"
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    print(f"Found {len(matches)} illustration blocks in Book {book_id}.")

    new_content = content
    scene_num = 1

    # --- Custom prompts path (Book 5 and future books without description blocks) ---
    if len(matches) == 0 and book_id == "5":
        custom_prompts = BOOK5_PROMPTS
        print(f"Using custom prompts for Book {book_id} ({len(custom_prompts)} entries).")

        for scene_key, desc in custom_prompts.items():
            if scene_key == "cover":
                # Generate cover as color only
                fname_color = f"{prefix}cover.jpg"
                save_color = image_dir / fname_color
                print(f"--- Book {book_id} | COVER | COLOR ---")
                if not save_color.exists():
                    print(f"Prompt: {desc[:50]}...")
                    url = generate_image(desc, is_bw=False)
                    if url:
                        download_image(url, save_color)
                        time.sleep(1)
                    else:
                        print(f"Skipping {fname_color} due to generation error.")
                else:
                    print(f"File {fname_color} already exists, skipping generation.")
                continue

            scene_index = scene_key
            # Generate both B&W and Color for each scene
            for suffix, is_bw in [("bw", True), ("color", False)]:
                fname = f"{prefix}{scene_index}_{suffix}.jpg"
                save_path = image_dir / fname

                print(f"--- Book {book_id} | Scene {scene_index} | {suffix.upper()} ---")

                if not save_path.exists():
                    print(f"Prompt: {desc[:50]}...")
                    url = generate_image(desc, is_bw=is_bw)
                    if url:
                        download_image(url, save_path)
                        time.sleep(1)
                    else:
                        print(f"Skipping {fname} due to generation error.")
                else:
                    print(f"File {fname} already exists, skipping generation.")

            # Replace inline image refs in manuscript if they exist
            bw_ref = f"![{prefix}{scene_index}_bw.jpg](images/{prefix}{scene_index}_bw.jpg)"
            color_ref = f"![{prefix}{scene_index}_color.jpg](images/{prefix}{scene_index}_color.jpg)"
            # These refs may already be in the manuscript; no replacement needed
    else:
        # --- Original regex-based path (Books 1, 2, 4) ---
        # Process blocks. Note: they come in pairs (B&W then Color)
        # If the manuscript structure is consistent, i=0,2,4... are B&W, i=1,3,5... are Color

        for i in range(len(matches)):
            m = matches[i]
            label_type = m.group(1)
            desc = m.group(2).strip()

            # Determine if B&W or Color based on label
            is_bw = "B&W" in label_type

            # Match scene numbering: i=0,1 (Scene 1), i=2,3 (Scene 2)
            scene_index = (i // 2) + 1
            suffix = "bw" if is_bw else "color"
            fname = f"{prefix}{scene_index}_{suffix}.jpg"
            save_path = image_dir / fname

            print(f"--- Book {book_id} | Scene {scene_index} | {suffix.upper()} ---")

            if not save_path.exists():
                print(f"Prompt: {desc[:50]}...")
                url = generate_image(desc, is_bw=is_bw)
                if url:
                    download_image(url, save_path)
                    time.sleep(1) # Small delay
                else:
                    print(f"Skipping {fname} due to generation error.")
                    continue
            else:
                print(f"File {fname} already exists, skipping generation.")

            # Replace in content with label for the other assistant
            # Requirement: "replace the description in the book, with the photo matching that description"
            # and "label the photos appropriately"

            assistant_note = f"\n> [ASSISTANT NOTE: Insert image '{fname}' here. Scene {scene_index} - {'Color' if not is_bw else 'B&W'}]\n"
            markdown_tag = f"![{fname}](images/{fname})\n{assistant_note}"

            # Replace the specific match instance
            old_block = m.group(0)
            new_content = new_content.replace(old_block, markdown_tag, 1)

    # Save the illustrated version
    output_fname = f"{manuscript_path.stem}_ILLUSTRATED.md"
    output_path = manuscript_path.parent / output_fname
    with open(output_path, 'w') as f:
        f.write(new_content)
    
    print(f"\n✅ Book {book_id} Processing Complete!")
    print(f"Illustrated manuscript: {output_path}")

if __name__ == "__main__":
    if API_KEY:
        for book_id in ["1", "2", "4", "5"]:
            print(f"\n========================================")
            print(f"STARTING BOOK {book_id}")
            print(f"========================================\n")
            process_book(book_id)
    else:
        print("API Key missing.")
