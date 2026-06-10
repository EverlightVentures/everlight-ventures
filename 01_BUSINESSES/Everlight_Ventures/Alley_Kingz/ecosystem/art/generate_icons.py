#!/usr/bin/env python3
"""
ALLEY KINGZ -- BATCH ICON / ARENA GENERATOR (pure Python stdlib, no pip deps)
=============================================================================

Generates the 48 unit icons + 3 arena maps for the Alley Kingz game by reading
the canonical roster (../data/cards.json) and the style reference
(../art/ART_PROMPT_PACK.md), then calling an image-generation backend.

This is BETA art meant to bootstrap the board off placeholder shapes. It is
expected to be upgraded later through the ART_BIBLE 3-stage review gate before
it becomes final, on-chain NFT art. Treat the first pass as scaffolding.

----------------------------------------------------------------------------
HOW TO RUN
----------------------------------------------------------------------------
Primary (Leonardo.ai, best render quality, fixed seed for consistency):

    LEONARDO_API_KEY=xxxxxxxx python3 generate_icons.py

Free fallback (HuggingFace Inference API, Flux/SDXL, returns bytes directly):

    HF_TOKEN=hf_xxxxxxxx python3 generate_icons.py

Useful flags:

    python3 generate_icons.py --force        # regen everything (ignore existing)
    python3 generate_icons.py --only 0001     # just one card by cardNumber
    python3 generate_icons.py --arena-only    # only the 3 arena maps
    python3 generate_icons.py --units-only    # only the 48 unit icons
    python3 generate_icons.py --delay 4       # seconds between API calls

If NEITHER env var is set, the script prints where to get a key and exits 0
WITHOUT erroring (so it is safe to wire into a pipeline that may run keyless).

----------------------------------------------------------------------------
COST NOTE
----------------------------------------------------------------------------
- Leonardo: ~150 free tokens/day on the free tier. A 1024x1024 Phoenix/Flux
  image is a few tokens; the full 51-asset set will likely span 2-3 days of the
  free allowance, OR a few dollars of a paid API plan. Re-runs are FREE because
  the script is idempotent (skips files that already exist; use --force to redo).
- HuggingFace: free Inference API has a rate limit; the script waits between
  calls and retries on the model-warming 503. Slower but $0.

----------------------------------------------------------------------------
OUTPUT (exactly the Delivery Spec paths from ART_PROMPT_PACK Section 6)
----------------------------------------------------------------------------
    assets/units/<cardNumber>_<slug>.png      e.g. 0001_bcardd.png   (1024 sq)
    assets/arena/<name>.png                    e.g. arena_a_neon_night.png

Files land straight into the workspace game/assets/ tree (which IS on the
phone), so the moment a PNG exists the game's icon preloader picks it up.

Pure stdlib only (urllib, json, base64, os, time, re, argparse). No Pillow,
no requests, no SDK -- nothing to pip-install on the phone proot.
"""

import os
import re
import sys
import json
import time
import base64
import argparse
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Paths (resolved relative to THIS file so it runs from anywhere)
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
CARDS_JSON = os.path.normpath(os.path.join(HERE, "..", "data", "cards.json"))
PROMPT_PACK = os.path.join(HERE, "ART_PROMPT_PACK.md")
GAME_DIR = os.path.normpath(os.path.join(HERE, "..", "game"))
UNITS_DIR = os.path.join(GAME_DIR, "assets", "units")
ARENA_DIR = os.path.join(GAME_DIR, "assets", "arena")
TOWERS_DIR = os.path.join(ARENA_DIR, "towers")

# Fixed seed locks the look across the whole set (per ART_PROMPT_PACK 1.2).
FIXED_SEED = 770118
ICON_SIZE = 1024   # Leonardo wants multiples of 8, max 1024; downscale later if wanted
ARENA_W, ARENA_H = 832, 1216  # ~ board 3:5 portrait, both multiples of 8

# ---------------------------------------------------------------------------
# Style Bible line + universal negative.
# Pulled live from ART_PROMPT_PACK.md Section 2 when present; the constants
# below are the verbatim fallback so the script is self-contained offline.
# ---------------------------------------------------------------------------
STYLE_BIBLE_FALLBACK = (
    "Small square mobile game unit icon, hyper-real stylized PBR render "
    "(Clash Royale clarity + Uncharted 4 texture fidelity), single subject "
    "centered and readable at 60px, dynamic 3/4 battle-ready pose, cyberpunk "
    "dog crew member piloting / mounted on a Twisted-Metal war-rig. Cinematic "
    "three-point lighting (warm key, cool fill, gold rim), volumetric haze, "
    "high contrast. Everlight palette: Crown Gold #D4AF37 / #c9a84c on "
    "vanta-black #050507, with the unit's faction accent. Consistent scale and "
    "camera across the whole set, full body fitting inside the square with a "
    "small margin, transparent background."
)
NEGATIVE_FALLBACK = (
    "no text, no letters, no numbers, no watermark, no signature, no logo "
    "overlay, no UI, no card frame, no border, no background scenery, no rum "
    "bottle, no liquor, no alcohol branding, low quality, blurry, 2D flat "
    "sprite, pixel art, flat cel shading, cartoon, anime, oversaturated, extra "
    "limbs, deformed dog anatomy, multiple subjects."
)

# Faction descriptor quick-keys (ART_PROMPT_PACK Section 2 accent guide).
FACTION_DESC = {
    "boneguard_crew": (
        "Boneguard Crew faction, amber and Brick Warm #C1440E war-paint over "
        "matte black, heavy armored brawler war-rig with bull-bars, riveted "
        "plate and a ram plow, tanky low and wide"
    ),
    "zoomie_syndicate": (
        "Zoomie Syndicate faction, magenta and Neon Cyan #00F5FF glow on jet "
        "black, low-slung speed rig with exposed turbines, blade fenders and "
        "nitro, fast and light"
    ),
    "leashbreak_tactix": (
        "Leashbreak Tactix faction, violet and cyan glyphs, matte hacker "
        "tech-van with antenna arrays, a holo dish and EMP emitters, disabler"
    ),
    "k9_circuitry": (
        "K9 Circuitry faction, teal with polished chrome and gold, turret-rig / "
        "drone-carrier with rail-cannons and drone bays, structure-breaker"
    ),
}

# 3 arena maps -- (filename, descriptor) from ART_PROMPT_PACK Section 5.
ARENA_FRAMING = (
    "Top-down slight-angle Clash-Royale-style battle board, vertical portrait "
    "orientation, two clear vertical combat lanes separated by a central "
    "divider with two side bridges crossing it, three tower pads per side (two "
    "forward princess pads plus one rear king/Alpha-Den pad), gold #D4AF37 "
    "faction paint marking the tower pads and lane edges, hyper-real PBR "
    "environment (Uncharted 4 city fidelity), cinematic lighting, readable "
    "uncluttered lanes for gameplay, vanta-black #050507 deep shadow. No "
    "characters, no units, no UI, no text."
)
ARENAS = [
    (
        "arena_a_neon_night",
        "A wet cyberpunk downtown street at neon-night, two lanes carved "
        "between glowing storefronts and skyscraper bases, a neon-lit canal as "
        "the central divider with two metal side bridges, cyan #00F5FF and "
        "magenta neon signage reflecting in the wet asphalt, gold #D4AF37 tower "
        "pads glowing, volumetric fog at the far intersection, Midnight Deep "
        "#0D0D1A shadow. Premium, electric, night-war mood.",
    ),
    (
        "arena_b_golden_industrial",
        "An industrial warehouse-district yard at golden hour, two lanes "
        "between corrugated-steel buildings and shipping containers, a dry "
        "concrete channel as the central divider with two steel-grate side "
        "bridges, warm amber low-sun rim light and long shadows on cracked "
        "asphalt, brick-warm #C1440E rust tones, gold #D4AF37 tower pads, dust "
        "motes in god-rays. Cinematic, gritty, daytime-war mood.",
    ),
    (
        "arena_c_rain_docks",
        "A neon harbor dock at night in the rain, two lanes along wet planked "
        "piers, dark water as the central divider with two rope-and-steel side "
        "bridges, teal #00F5FF and gold reflections rippling on the rain-slick "
        "boards, cargo cranes silhouetted, gold #D4AF37 tower pads, heavy rain "
        "streaks and puddle reflections, volumetric mist. Moody, reflective, "
        "storm-war mood.",
    ),
    (
        "the_lot",
        "A gritty rusted urban junk lot at dusk, the humble STARTING battleground, "
        "two dirt-and-gravel lanes between stacks of rusted junk cars and chain-link "
        "fences, a dry cracked ditch as the central divider with two plank-and-scrap "
        "side bridges, warm dusty low light, rust-brown faded tones with a few gold "
        "#D4AF37 tower pads, graffiti on concrete barriers, weeds in the cracks. "
        "Gritty, humble, where-it-all-begins mood.",
    ),
]

# ---------------------------------------------------------------------------
# TOWER SKINS -- per-arena themed tower decals (the game draws them filling the
# tower's square face, then paints the owner-color frame + HP on top). NO
# transparency: each is a solid square that fills the frame. Two per arena:
#   princess "Pack Guard" (forward, fortified) + king "Alpha Den" (rear, taller
#   and grander). Match each arena's palette so towers sit in their world.
# Output: assets/arena/towers/<arena>_princess.png and <arena>_king.png (6 files).
# ---------------------------------------------------------------------------
TOWER_FRAMING = (
    "a square frontal game tower decal, fills the frame, {theme}, a fortified "
    "{role} tower with the Alley Kingz dog-crew faction motif and gold #D4AF37 "
    "trim, hyper-real PBR, readable at small size, NO transparency, NO text, NO "
    "watermark, solid framed art that fills the square."
)
TOWER_THEMES = {
    "arena_a_neon_night": (
        "wet cyberpunk neon-night materials, brushed dark metal and glowing "
        "panels in neon cyan #00F5FF and magenta, rain-slick reflective surfaces"
    ),
    "arena_b_golden_industrial": (
        "golden-hour industrial materials, rusted corrugated steel and amber "
        "warm light, brick-warm #C1440E rust tones with riveted plate"
    ),
    "arena_c_rain_docks": (
        "rain-soaked harbor-dock materials, teal #00F5FF and weathered steel, "
        "wet planking and cargo-crate panels with storm-grey reflections"
    ),
    "the_lot": (
        "rusted scrapyard materials, weathered junk-metal and chain-link fencing, "
        "rust-brown and faded paint, makeshift scrap-plated fortifications with a "
        "little gold #D4AF37 trim"
    ),
}
# (arena, type, role-phrase). King is taller / grander than the princess.
TOWER_ROLES = [
    ("princess", "princess pack-guard"),
    ("king", "taller king alpha-den"),
]


def build_tower_prompt(arena_name, role_phrase):
    theme = TOWER_THEMES.get(arena_name, "Alley Kingz cyberpunk materials")
    return TOWER_FRAMING.format(theme=theme, role=role_phrase)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(name):
    """lowercase, non-alphanumeric -> underscore (matches the game preloader)."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def load_style_bible():
    """Pull the Style Bible line + Universal Negative from the prompt pack if
    available, else use the in-file fallback so we never depend on the .md."""
    style, negative = STYLE_BIBLE_FALLBACK, NEGATIVE_FALLBACK
    try:
        with open(PROMPT_PACK, "r", encoding="utf-8") as fh:
            txt = fh.read()
        # Section 2 lines start with bold markers. Grab the backtick-wrapped body.
        m = re.search(r"PREPEND -- locked style:\*\*\s*`([^`]+)`", txt)
        if m:
            style = m.group(1).strip()
        m = re.search(r"UNIVERSAL NEGATIVE -- append to EVERY icon prompt:\*\*\s*`([^`]+)`", txt)
        if m:
            negative = m.group(1).strip()
    except (OSError, UnicodeDecodeError):
        pass
    return style, negative


def build_card_prompt(card, style_line):
    """Style Bible line + per-card descriptor (breed + faction + role + rig)."""
    faction = FACTION_DESC.get(card.get("factionId", ""), "Alley Kingz cyberpunk war-rig")
    rig = card.get("rig", {}) or {}
    rig_name = rig.get("name", "war-rig")
    rig_flavor = rig.get("flavor") or rig.get("rigLanguage") or ""
    descriptor = (
        "A {breed} dog as an Alley Kingz war-crew {role}, named {name}. {faction}. "
        "Mounted on / piloting {rig_name}: {rig_flavor}. Dynamic 3/4 battle pose, "
        "small square game unit icon, clean transparent background."
    ).format(
        breed=card.get("breed", "dog"),
        role=card.get("role", "fighter"),
        name=card.get("name", "unit"),
        faction=faction,
        rig_name=rig_name,
        rig_flavor=rig_flavor.strip() if rig_flavor else "armored battle vehicle",
    )
    return "{style} {desc}".format(style=style_line, desc=descriptor)


def build_arena_prompt(descriptor):
    return "{framing} {desc}".format(framing=ARENA_FRAMING, desc=descriptor)


def http_json(url, method="GET", headers=None, body=None, timeout=120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_bytes(url, timeout=180):
    req = urllib.request.Request(url, method="GET")
    # Leonardo's CDN (cdn.leonardo.ai) 403s the default Python urllib User-Agent.
    # A browser-like UA returns 200. (Confirmed by isolating poll vs download.)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_image(data, out, box=None):
    """Write bytes to `out`. If Pillow is available and `box` is set, downscale
    to a box x box PNG (game-ready, small ~100KB) so 48 icons do not bloat the
    page to 50MB+. Falls back to writing raw bytes if Pillow is missing."""
    if box:
        try:
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGBA")
            im.thumbnail((box, box), Image.LANCZOS)
            im.save(out, "PNG", optimize=True)
            return os.path.getsize(out)
        except Exception:
            pass  # Pillow missing or decode failed -> raw write below
    with open(out, "wb") as fh:
        fh.write(data)
    return len(data)


# ---------------------------------------------------------------------------
# Backend: LEONARDO.AI
# Flow (Leonardo REST v1, https://cloud.leonardo.ai/api/rest/v1):
#   1. POST /generations  with Bearer key + prompt/model/seed -> { sdGenerationJob: { generationId } }
#   2. GET  /generations/{id}  poll until generations_by_pk.status == "COMPLETE"
#   3. read generated_images[0].url (https://cdn.leonardo.ai/...) -> download bytes
# Model: Leonardo Phoenix 1.0 (good for stylized game art); fixed seed for set
# consistency; transparency=true requests an alpha cut where the model supports it.
# ---------------------------------------------------------------------------
LEONARDO_BASE = "https://cloud.leonardo.ai/api/rest/v1"
# Leonardo Phoenix 1.0 -- strong stylized illustration / game-asset model.
LEONARDO_MODEL_ID = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"


def leonardo_generate(prompt, w, h, api_key, negative=""):
    headers = {
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    }
    payload = {
        "prompt": prompt,
        "modelId": LEONARDO_MODEL_ID,
        "width": w,
        "height": h,
        "num_images": 1,
        "seed": FIXED_SEED,          # lock the look across the whole set
        "alchemy": True,             # higher fidelity pipeline (proven OK with Phoenix 1.0)
        # NOTE: Leonardo "transparency" 400s on this model/account (only disabled|
        # foreground_only are valid values AND the feature is not enabled here), so
        # we skip it. The game clips icons into a round token + draws the rarity
        # frame on top, so the square background is masked. Premium pass can do a
        # transparent model or rembg on e5 later.
        "public": False,
    }
    if negative:
        payload["negative_prompt"] = negative
    # 1. kick off the generation
    job = http_json(LEONARDO_BASE + "/generations", method="POST",
                    headers=headers, body=payload)
    gen_id = (job.get("sdGenerationJob") or {}).get("generationId")
    if not gen_id:
        raise RuntimeError("Leonardo: no generationId in response: " + json.dumps(job)[:300])
    # 2. poll until COMPLETE
    for _ in range(60):  # ~ up to 3 min at 3s intervals
        time.sleep(3)
        try:
            status = http_json(LEONARDO_BASE + "/generations/" + gen_id,
                               method="GET", headers=headers)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                continue
            raise
        gen = status.get("generations_by_pk") or {}
        st = gen.get("status")
        if st == "COMPLETE":
            imgs = gen.get("generated_images") or []
            if not imgs or not imgs[0].get("url"):
                raise RuntimeError("Leonardo: COMPLETE but no image url")
            # 3. download the result PNG
            return http_bytes(imgs[0]["url"])
        if st == "FAILED":
            raise RuntimeError("Leonardo: generation FAILED")
    raise RuntimeError("Leonardo: timed out waiting for COMPLETE")


# ---------------------------------------------------------------------------
# Backend: HUGGINGFACE FREE (Inference API)
# POST https://api-inference.huggingface.co/models/<model> with Bearer token;
# the response body IS the raw image bytes (or JSON {error,estimated_time} on a
# cold model -> we wait and retry).
# ---------------------------------------------------------------------------
HF_MODEL = "black-forest-labs/FLUX.1-schnell"  # fast, free, good quality


def hf_generate(prompt, w, h, token, negative=""):
    url = "https://api-inference.huggingface.co/models/" + HF_MODEL
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "image/png",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {"width": w, "height": h, "seed": FIXED_SEED},
        "options": {"wait_for_model": True},
    }
    if negative:
        payload["parameters"]["negative_prompt"] = negative
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method="POST")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
            # If HF returns JSON it is an error / warming notice, not an image.
            if raw[:1] in (b"{", b"["):
                info = json.loads(raw.decode("utf-8", "replace"))
                wait = float(info.get("estimated_time", 12))
                print("    HF model warming, waiting %.0fs..." % wait)
                time.sleep(min(wait, 30))
                continue
            return raw
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print("    HF busy (%d), backing off..." % e.code)
                time.sleep(15)
                continue
            raise
    raise RuntimeError("HuggingFace: exhausted retries")


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
def pick_backend():
    """Return (name, fn(prompt,w,h,negative)->png_bytes) or (None, None)."""
    leo = os.environ.get("LEONARDO_API_KEY")
    hf = os.environ.get("HF_TOKEN")
    if leo:
        return "LEONARDO", (lambda p, w, h, neg="": leonardo_generate(p, w, h, leo, neg))
    if hf:
        return "HF_FREE", (lambda p, w, h, neg="": hf_generate(p, w, h, hf, neg))
    return None, None


def generate(prompt, w, h, backend_fn, negative=""):
    """Backend abstraction: prompt -> png_bytes via the selected backend."""
    return backend_fn(prompt, w, h, negative)


def print_keyless_help():
    print("")
    print("No image backend configured. Set ONE of these env vars and re-run:")
    print("")
    print("  LEONARDO_API_KEY   (primary, best quality)")
    print("    -> Sign in at https://app.leonardo.ai  ->  user menu  ->  API Access")
    print("    -> Create a key (free tier ~150 tokens/day). Then:")
    print("       LEONARDO_API_KEY=xxxx python3 generate_icons.py")
    print("")
    print("  HF_TOKEN           (free fallback, slower)")
    print("    -> Sign in at https://huggingface.co  ->  Settings  ->  Access Tokens")
    print("    -> Create a free read token (hf_...). Then:")
    print("       HF_TOKEN=hf_xxxx python3 generate_icons.py")
    print("")
    print("This is beta art to be upgraded later. Re-runs are idempotent (skip "
          "existing files; use --force to regenerate).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Alley Kingz icon/arena generator (stdlib).")
    ap.add_argument("--force", action="store_true", help="regenerate even if file exists")
    ap.add_argument("--only", default=None, help="only this cardNumber, e.g. 0001")
    ap.add_argument("--arena-only", action="store_true", help="only the 3 arena maps")
    ap.add_argument("--units-only", action="store_true", help="only the 48 unit icons")
    ap.add_argument("--towers-only", action="store_true", help="only the 6 tower skins")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between API calls")
    args = ap.parse_args()

    backend_name, backend_fn = pick_backend()
    if backend_fn is None:
        print_keyless_help()
        return 0  # not an error -- safe in a keyless pipeline

    print("Backend: %s | seed=%d" % (backend_name, FIXED_SEED))
    style_line, negative = load_style_bible()

    with open(CARDS_JSON, "r", encoding="utf-8") as fh:
        cards = json.load(fh)["cards"]

    os.makedirs(UNITS_DIR, exist_ok=True)
    os.makedirs(ARENA_DIR, exist_ok=True)
    os.makedirs(TOWERS_DIR, exist_ok=True)

    # Which lanes run? An explicit --x-only flag isolates that lane; otherwise
    # the default full run does units + arenas + towers.
    want_units = (not args.arena_only and not args.towers_only)
    want_arena = (not args.units_only and not args.towers_only and not args.only)
    want_towers = (not args.units_only and not args.arena_only and not args.only)

    # Build the work list of (kind, label, out_path, prompt, w, h).
    jobs = []
    if want_units:
        for card in cards:
            num = card["cardNumber"]
            if args.only and num != args.only:
                continue
            fname = "%s_%s.png" % (num, slugify(card["name"]))
            out = os.path.join(UNITS_DIR, fname)
            prompt = build_card_prompt(card, style_line) + " " + negative
            jobs.append(("unit", fname, out, prompt, ICON_SIZE, ICON_SIZE))
    if want_arena:
        for name, desc in ARENAS:
            out = os.path.join(ARENA_DIR, name + ".png")
            prompt = build_arena_prompt(desc) + " " + negative
            jobs.append(("arena", name + ".png", out, prompt, ARENA_W, ARENA_H))
    if want_towers:
        for arena_name, _desc in ARENAS:
            for ttype, role_phrase in TOWER_ROLES:
                fname = "%s_%s.png" % (arena_name, ttype)
                out = os.path.join(TOWERS_DIR, fname)
                prompt = build_tower_prompt(arena_name, role_phrase) + " " + negative
                jobs.append(("tower", fname, out, prompt, 512, 512))

    total = len(jobs)
    made = skipped = failed = 0
    for i, (kind, label, out, prompt, w, h) in enumerate(jobs, 1):
        tag = "[%d/%d] %s" % (i, total, label)
        if os.path.exists(out) and not args.force:
            print("%s -- skip (exists)" % tag)
            skipped += 1
            continue
        try:
            print("%s -- generating (%dx%d)..." % (tag, w, h))
            png = generate(prompt, w, h, backend_fn, negative)
            nbytes = save_image(png, out, 512 if kind in ("unit", "tower") else None)
            print("        saved -> %s (%d bytes)" % (out, nbytes))
            made += 1
        except Exception as e:  # keep grinding the rest of the set
            print("        FAILED: %s" % e)
            failed += 1
        if i < total:
            time.sleep(max(0.0, args.delay))  # rate-limit friendly

    print("")
    print("Done. made=%d skipped=%d failed=%d (of %d)" % (made, skipped, failed, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
