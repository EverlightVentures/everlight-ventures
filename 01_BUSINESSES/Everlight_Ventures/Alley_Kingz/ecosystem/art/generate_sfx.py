#!/usr/bin/env python3
"""
ALLEY KINGZ -- BATTLE SFX GENERATOR (ElevenLabs Sound Effects, pure stdlib)
==========================================================================
Generates the game's battle sound effects via the ElevenLabs sound-generation
API and saves them as small mp3s into the game's assets/sfx/ folder. The engine
plays the matching sample per event (with the old synth tones as fallback).

Smart-scoped: sounds are keyed by EVENT + WEAPON TYPE (not 48 unique per card),
so the battlefield sounds varied + systematic without a huge set. The 4 Mythics
share a signature 'bark'. Heavy/arena sounds (tower_down) read big.

RUN:  ELEVENLABS_API_KEY=sk_xxxx python3 generate_sfx.py
      python3 generate_sfx.py --force   # regen all (else skip existing)
Pure stdlib (urllib/json/os). No pip deps -- runs on the phone.
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.normpath(os.path.join(HERE, "..", "game", "assets", "sfx"))
API = "https://api.elevenlabs.io/v1/sound-generation"

# name -> (prompt, duration_seconds). Names match engine.js sfx() lookups.
MANIFEST = {
  "deploy":     ("a unit dropping into battle, a solid mechanical thud with a short energized power-up whoosh, clean game deploy sound, no music", 1.0),
  "atk_bullet": ("rapid sharp automatic gunfire, crisp metallic bullet shots, punchy, game weapon sfx, no music", 0.9),
  "atk_cannon": ("a heavy cannon firing a large shell, deep powerful boom with recoil thump, game artillery, no music", 1.3),
  "atk_beam":   ("a sci-fi energy beam laser firing, electric crackling zap, futuristic game weapon, no music", 0.9),
  "atk_lance":  ("a piercing energy lance shot, sharp whoosh then a cracking impact, game weapon, no music", 0.8),
  "atk_spread": ("a scatter burst of multiple pellets firing at once, shotgun-like spread, game weapon, no music", 0.9),
  "atk_melee":  ("a heavy armored melee slam, metal ram impact with a clang and crunch, game melee, no music", 0.8),
  "death":      ("a battle unit exploding and breaking apart, metal debris and a short crunch, game death sfx, no music", 1.1),
  "tower_hit":  ("a heavy projectile slamming into a metal fortified structure, deep thud impact, no music", 0.7),
  "tower_down": ("a large tower structure collapsing and exploding, beams snapping, heavy debris crash and rumble, cinematic, no music", 2.2),
  "ability":    ("a powerful special ability activating, rising magical-tech energy shimmer with a pulse, game skill sfx, no music", 1.0),
  "win":        ("a short triumphant heroic victory fanfare sting, brassy and bold, game win jingle", 2.5),
  "lose":       ("a short somber defeat sting, descending sad tone, game loss jingle", 2.0),
  "bark":       ("a single deep powerful war-dog bark, aggressive guard dog, short and punchy, no music", 0.7),
}

def gen(name, prompt, dur, key, force):
    out = os.path.join(SFX_DIR, name + ".mp3")
    if os.path.exists(out) and not force:
        print("  skip (exists):", name); return "skip"
    body = json.dumps({"text": prompt, "duration_seconds": dur, "prompt_influence": 0.5}).encode()
    req = urllib.request.Request(API, data=body, method="POST")
    req.add_header("xi-api-key", key); req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        if data[:3] not in (b"ID3", b"\xff\xfb", b"\xff\xf3"):
            print("  WARN", name, "not mp3:", data[:40]); return "fail"
        with open(out, "wb") as fh: fh.write(data)
        print("  saved:", name, "(%d bytes)" % len(data)); return "made"
    except urllib.error.HTTPError as e:
        print("  FAIL", name, "HTTP", e.code, e.read().decode("utf-8","replace")[:160]); return "fail"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("Set ELEVENLABS_API_KEY=sk_... and re-run. (Found in 03_Credentials/.env)"); return 0
    os.makedirs(SFX_DIR, exist_ok=True)
    made = skip = fail = 0
    items = list(MANIFEST.items())
    for i, (name, (prompt, dur)) in enumerate(items, 1):
        print("[%d/%d]" % (i, len(items)), name)
        r = gen(name, prompt, dur, key, args.force)
        made += r == "made"; skip += r == "skip"; fail += r == "fail"
        if i < len(items): time.sleep(args.delay)
    print("\nDone. made=%d skip=%d fail=%d -> %s" % (made, skip, fail, SFX_DIR))
    return 0

if __name__ == "__main__":
    sys.exit(main())
