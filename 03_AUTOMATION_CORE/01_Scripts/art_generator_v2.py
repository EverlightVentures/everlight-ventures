#!/usr/bin/env python3
"""
Alley Kingz -- Art Generator v2
Gemini Vision image-to-text pipeline for hyper-real game asset prompt extraction.

Usage:
    python3 art_generator_v2.py --input /path/to/reference_images/ --style legendary_card
    python3 art_generator_v2.py --image /path/to/single.png --style character

Outputs:
    - prompts saved to: Alley_Kingz_V2_Assets/06_AI_Prompts/Generated/
    - manifest entry appended to: content_pack.json
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

ASSET_ROOT = Path(
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures"
    "/01_OnyxPOS/Alley_Kingz_V2_Assets"
)
PROMPT_OUTPUT_DIR = ASSET_ROOT / "06_AI_Prompts" / "Generated"
MANIFEST_PATH = ASSET_ROOT / "content_pack.json"

ART_BIBLE_STYLE_DIRECTIVES = {
    "character": (
        "Hyper-realistic street culture character for a mobile card battle game. "
        "Style: Clash Royale clarity + Uncharted 4 texture fidelity. "
        "PBR materials: subsurface scattering on skin, leather creases, fabric drape. "
        "Lighting: golden hour urban rim light + neon night fill. "
        "Heroic proportions, 3/4 angle pose, decisive expression. "
        "Color palette anchors: Crown Gold (#D4AF37), Midnight Deep (#0D0D1A). "
        "Mobile LOD spec: 45K polys max, 2K texture atlas, ASTC 6x6 compression. "
        "Include: lighting description, texture detail, color palette, mood, polycount hints."
    ),
    "common_card": (
        "Common rarity card art for Alley Kingz mobile card battle game. "
        "Style: stylized hyper-realism, Asphalt Grey (#4A4A55) brushed steel border, matte frame. "
        "Urban street scene, painterly but hyper-real -- think Uncharted 4 environment art. "
        "Subdued palette: warm tans, muted greens, brick red. Subject fills 70% of card. "
        "Art bleeds to edge, no white border. "
        "Mobile spec: 2K texture, ASTC compressed."
    ),
    "rare_card": (
        "Rare rarity card art for Alley Kingz mobile card battle game. "
        "Blue chrome border, subtle pulse glow, polished chrome frame. "
        "Hyper-real urban scene with faction identity. High contrast. "
        "Crown Gold (#D4AF37) and Neon Cyan (#00F5FF) accents. "
        "Mobile spec: 2K texture, ASTC compressed."
    ),
    "epic_card": (
        "Epic rarity card art for Alley Kingz mobile card battle game. "
        "Brick/orange flame border, ember particle sparks, hammered copper frame. "
        "Dramatic scene, cinematic lighting, faction power on display. "
        "Brick Warm (#C1440E) dominant, Crown Gold (#D4AF37) accent. "
        "Mobile spec: 2K texture, ASTC compressed."
    ),
    "legendary_card": (
        "Legendary rarity card art for Alley Kingz mobile card battle game. "
        "Crown Gold holographic border, radiant crown glow pulse, gold foil embossed frame. "
        "Maximum visual impact: volumetric lighting, particle aura, cinematic moment. "
        "Crown Gold (#D4AF37) + Neon Cyan (#00F5FF) + Midnight Deep (#0D0D1A). "
        "Mobile spec: 2K texture, ASTC compressed. Must read at 200x300px thumbnail."
    ),
    "area_map": (
        "Isometric 45-degree urban battle map area for Alley Kingz mobile card game. "
        "Hyper-real environment: PBR concrete, wet asphalt reflections, volumetric fog. "
        "Environmental storytelling: 1 faction mark, 1 hazard, 1 ambient life element. "
        "Golden hour OR neon night -- not ambiguous. "
        "Mobile LOD: max 2K texture, max 50K poly per scene, ASTC/ETC2 compressed."
    ),
    "shop_ui": (
        "In-game shop UI element for Alley Kingz mobile card game. "
        "Underground luxury aesthetic: frosted glass panels, Crown Gold (#D4AF37) trim. "
        "Featured item as 3D holographic projection. Neon accents. "
        "Optimized for mobile: PNG-8 where possible, 1K sprite atlases."
    ),
    "marketing": (
        "App store / social marketing render for Alley Kingz mobile card battle game. "
        "Hyper-real character power moment or card battle scene. "
        "Maximum visual quality -- this is NOT mobile-optimized, it is a marketing render. "
        "Designed to communicate premium card battle game at a glance. "
        "Clash Royale clarity, Street Fighter 6 character presence, NBA TopShot card drama."
    ),
}

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def load_image_bytes(image_path: Path) -> tuple[bytes, str]:
    """Load image and return (bytes, mime_type)."""
    ext = image_path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    if ext not in mime_map:
        raise ValueError(f"Unsupported image format: {ext}")
    return image_path.read_bytes(), mime_map[ext]


def build_prompt(style: str) -> str:
    directive = ART_BIBLE_STYLE_DIRECTIVES.get(style)
    if not directive:
        available = ", ".join(ART_BIBLE_STYLE_DIRECTIVES.keys())
        raise ValueError(f"Unknown style '{style}'. Available: {available}")
    return (
        f"You are an expert game art director for a 2026 mobile card battle game called Alley Kingz. "
        f"Analyze this reference image and describe it as a production-ready hyper-realistic game art prompt. "
        f"{directive} "
        f"Output format: A single detailed paragraph prompt (150-250 words) suitable for Midjourney, "
        f"SDXL, or ComfyUI. Include specific values for: lighting angle, texture keywords, "
        f"color hex anchors, mood descriptors, technical mobile spec notes."
    )


def extract_prompt_via_gemini(image_path: Path, style: str) -> str:
    """
    Call Gemini Pro Vision to convert a reference image into a hyper-real art prompt.
    Requires: GEMINI_API_KEY environment variable.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    img_bytes, mime_type = load_image_bytes(image_path)
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt_text = build_prompt(style)

    response = model.generate_content([
        prompt_text,
        {"mime_type": mime_type, "data": img_b64}
    ])
    return response.text.strip()


def save_prompt(image_path: Path, style: str, prompt_text: str) -> Path:
    """Save generated prompt to the output directory with structured filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = image_path.stem.replace(" ", "_")
    filename = f"{timestamp}_{style}_{stem}_prompt.txt"
    output_path = PROMPT_OUTPUT_DIR / filename
    PROMPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt_text, encoding="utf-8")
    return output_path


def update_manifest(image_path: Path, style: str, prompt_path: Path) -> None:
    """Append entry to content_pack.json manifest."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"version": "2.0", "assets": [], "generated_at": None}

    entry = {
        "source_image": str(image_path),
        "style": style,
        "prompt_file": str(prompt_path),
        "status": "ai_draft",
        "review_status": "pending",
        "created_at": datetime.now().isoformat(),
        "pbr_maps": [],
        "lod_levels": [],
        "ai_prompt_metadata": {
            "model": "gemini-1.5-pro",
            "style_directive": style,
        }
    }
    manifest["assets"].append(entry)
    manifest["generated_at"] = datetime.now().isoformat()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def process_image(image_path: Path, style: str, dry_run: bool = False) -> None:
    print(f"  Processing: {image_path.name} [{style}]")
    if dry_run:
        prompt_text = (
            f"[DRY RUN] Would extract hyper-real {style} prompt from {image_path.name}. "
            f"Style directive: {ART_BIBLE_STYLE_DIRECTIVES.get(style, 'unknown')[:80]}..."
        )
    else:
        prompt_text = extract_prompt_via_gemini(image_path, style)

    prompt_path = save_prompt(image_path, style, prompt_text)
    update_manifest(image_path, style, prompt_path)
    print(f"  Saved: {prompt_path.name}")
    print(f"  Preview: {prompt_text[:120]}...")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Alley Kingz Art Generator v2 -- Gemini image-to-prompt pipeline"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Single reference image path")
    group.add_argument("--input", type=Path, help="Directory of reference images")
    parser.add_argument(
        "--style",
        required=True,
        choices=list(ART_BIBLE_STYLE_DIRECTIVES.keys()),
        help="Art style / asset type to generate prompt for"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without calling Gemini API (for testing pipeline)"
    )
    args = parser.parse_args()

    print("Alley Kingz Art Generator v2")
    print(f"Style: {args.style}")
    print(f"Output dir: {PROMPT_OUTPUT_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")
    print()

    if args.image:
        if not args.image.exists():
            print(f"ERROR: Image not found: {args.image}")
            sys.exit(1)
        process_image(args.image, args.style, dry_run=args.dry_run)

    elif args.input:
        if not args.input.is_dir():
            print(f"ERROR: Directory not found: {args.input}")
            sys.exit(1)
        images = [
            p for p in args.input.iterdir()
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not images:
            print(f"No supported images found in {args.input}")
            sys.exit(1)
        print(f"Found {len(images)} images to process...")
        print()
        for img in sorted(images):
            process_image(img, args.style, dry_run=args.dry_run)

    print("Done. Review generated prompts in:")
    print(f"  {PROMPT_OUTPUT_DIR}")
    print("Move approved prompts to 06_AI_Prompts/Reviewed/ before sending to generation tools.")


if __name__ == "__main__":
    main()
