#!/usr/bin/env python3
"""
ALLEY KINGZ -- COMBAT/STORM SENSORY ASSET GENERATOR (pure stdlib)
================================================================
Generates the NEW sensory layer for the spells + Storm Clock + B-Card:
  SFX (ElevenLabs sound-generation)  -> game/assets/sfx/*.mp3
  Spell icons + B-Card (Leonardo)    -> game/assets/spells/*.png + assets/ui/bcard_emblem.png
Idempotent (skips existing; --force to redo). Continues on per-asset failure.

RUN:
  ELEVENLABS_API_KEY=sk_... LEONARDO_API_KEY=xxxx python3 generate_combat_assets.py
"""
import os, sys, json, time, base64, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.normpath(os.path.join(HERE, "..", "game"))
SFX_DIR = os.path.join(GAME, "assets", "sfx")
SPELL_DIR = os.path.join(GAME, "assets", "spells")
UI_DIR = os.path.join(GAME, "assets", "ui")

# ---- SFX (ElevenLabs sound-generation) : name -> (prompt, seconds) ----
SFX = {
  "spell_freeze":   ("a magical ice freeze spell crystallizing, sharp frost shatter with a cold shimmer, game spell cast, no music", 1.2),
  "spell_tar":      ("a thick tar goo splat spreading and bubbling, sticky slow debuff, game spell cast, no music", 1.2),
  "spell_snare":    ("a metal snare trap snapping shut, sharp clang and chain rattle, game trap trigger, no music", 1.0),
  "spell_jolt":     ("a sharp electric zap burst, crackling lightning discharge, game shock spell, no music", 0.9),
  "spell_strike":   ("a powerful fiery explosion striking from above, deep boom with debris, game fireball impact, no music", 1.3),
  "storm_lightning":("a sky lightning bolt striking the ground, sharp electric crack then rumbling thunder, no music", 1.4),
  "storm_flood":    ("a surging flood of water rushing in fast, heavy wet whoosh and splashing, no music", 1.6),
  "storm_scraprain":("scrap metal debris raining down and clattering hard on the ground, heavy metallic hail, no music", 1.6),
  "storm_drone":    ("a swarm of drones strafing overhead, mechanical buzzing whir with a fast strafing pass, no music", 1.4),
  "golden_hour":    ("a warm magical blessing aura activating, uplifting shimmering chime and glowing pulse, game buff zone, no music", 1.5),
}

# ---- Leonardo icons : name -> (subject prompt, allow_letters) ----
ICON_STYLE = ("Small square mobile-game SPELL card icon, hyper-real stylized PBR render, single centered "
              "readable symbol, cyberpunk, Everlight palette crown gold #D4AF37 on vanta-black #050507, "
              "dramatic glow, premium. ")
ICON_NEG = ("no text, no letters, no numbers, no watermark, no border, no card frame, low quality, blurry, "
            "flat 2d sprite, multiple subjects.")
SPELLS = {
  "freeze": (ICON_STYLE + "A Boneguard frost-blast glyph: a crystalline ice-shatter burst in icy blue-white over amber accents, freezing energy radiating out.", False),
  "tar":    (ICON_STYLE + "A Leashbreak tar-slow glyph: a splatter of glowing violet tar and tech-hex web goo, sticky oozing debuff.", False),
  "snare":  (ICON_STYLE + "A K9 snare-trap glyph: a chrome bear-trap and circuit-snare device with teal energy, coiled and ready to spring.", False),
  "jolt":   (ICON_STYLE + "A Zoomie jolt glyph: a sharp forked lightning zap bolt in neon magenta and cyan, crackling electric discharge.", False),
  "strike": (ICON_STYLE + "A Strike glyph: a fiery meteor/missile streaking down with a gold-orange explosion burst, impact shockwave.", False),
}
BCARD = ("A premium casino playing-card emblem, dark near-black card face with a thin glowing gold border, "
         "the rank symbol is a bold gold capital letter B with a small regal crown resting on top of it, "
         "ONE large crowned-B centered plus a small matching crowned-B in each of the four corners like "
         "playing-card rank pips, cyberpunk luxury, gold #D4AF37 on black, subtle neon edge glow, clean "
         "vector-like logo, centered, square. no watermark, no extra text beyond the letter B.")

LEO = "https://cloud.leonardo.ai/api/rest/v1"
LEO_MODEL = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"  # Phoenix 1.0

def _bytes(url, t=180):
    r = urllib.request.Request(url, method="GET"); r.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(r, timeout=t) as resp: return resp.read()

def gen_sfx(name, prompt, dur, key, force):
    out = os.path.join(SFX_DIR, name + ".mp3")
    if os.path.exists(out) and not force: print("  skip", name); return "skip"
    body = json.dumps({"text": prompt, "duration_seconds": dur, "prompt_influence": 0.5}).encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation", data=body, method="POST")
    req.add_header("xi-api-key", key); req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r: data = r.read()
        if data[:3] not in (b"ID3", b"\xff\xfb", b"\xff\xf3"): print("  WARN", name, "not mp3"); return "fail"
        open(out, "wb").write(data); print("  SFX", name, len(data), "b"); return "made"
    except urllib.error.HTTPError as e:
        print("  FAIL", name, e.code, e.read().decode("utf-8","replace")[:120]); return "fail"

def gen_icon(out, prompt, key, neg, force):
    if os.path.exists(out) and not force: print("  skip", os.path.basename(out)); return "skip"
    h = {"Authorization": "Bearer " + key, "Accept": "application/json", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "modelId": LEO_MODEL, "width": 512, "height": 512, "num_images": 1, "alchemy": True, "public": False}
    if neg: payload["negative_prompt"] = neg
    try:
        req = urllib.request.Request(LEO + "/generations", data=json.dumps(payload).encode(), method="POST")
        for k, v in h.items(): req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=120) as r: job = json.loads(r.read())
        gid = (job.get("sdGenerationJob") or {}).get("generationId")
        if not gid: print("  FAIL", os.path.basename(out), "no gen id", json.dumps(job)[:120]); return "fail"
        for _ in range(60):
            time.sleep(3)
            req = urllib.request.Request(LEO + "/generations/" + gid, method="GET")
            for k, v in h.items(): req.add_header(k, v)
            try:
                with urllib.request.urlopen(req, timeout=60) as r: st = json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429,500,502,503): continue
                raise
            g = st.get("generations_by_pk") or {}
            if g.get("status") == "COMPLETE":
                imgs = g.get("generated_images") or []
                if imgs and imgs[0].get("url"):
                    open(out, "wb").write(_bytes(imgs[0]["url"])); print("  ICON", os.path.basename(out)); return "made"
                print("  FAIL", os.path.basename(out), "no url"); return "fail"
            if g.get("status") == "FAILED": print("  FAIL", os.path.basename(out), "gen FAILED"); return "fail"
        print("  FAIL", os.path.basename(out), "timeout"); return "fail"
    except Exception as e:
        print("  FAIL", os.path.basename(out), str(e)[:140]); return "fail"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); ap.add_argument("--delay", type=float, default=1.5)
    a = ap.parse_args()
    el = os.environ.get("ELEVENLABS_API_KEY"); leo = os.environ.get("LEONARDO_API_KEY")
    os.makedirs(SFX_DIR, exist_ok=True); os.makedirs(SPELL_DIR, exist_ok=True); os.makedirs(UI_DIR, exist_ok=True)
    res = {"made":0,"skip":0,"fail":0}
    if el:
        print("== SFX (ElevenLabs) ==")
        for i,(n,(p,d)) in enumerate(SFX.items()):
            res[gen_sfx(n,p,d,el,a.force)] += 1
            if i < len(SFX)-1: time.sleep(a.delay)
    else: print("== SFX SKIPPED (no ELEVENLABS_API_KEY) ==")
    if leo:
        print("== ICONS (Leonardo) ==")
        for n,(p,_al) in SPELLS.items():
            res[gen_icon(os.path.join(SPELL_DIR, n+".png"), p, leo, ICON_NEG, a.force)] += 1; time.sleep(a.delay)
        res[gen_icon(os.path.join(UI_DIR, "bcard_emblem.png"), BCARD, leo, "low quality, blurry, watermark", a.force)] += 1
    else: print("== ICONS SKIPPED (no LEONARDO_API_KEY) ==")
    print("\nDONE made=%d skip=%d fail=%d" % (res["made"],res["skip"],res["fail"]))
    return 0

if __name__ == "__main__": sys.exit(main())
