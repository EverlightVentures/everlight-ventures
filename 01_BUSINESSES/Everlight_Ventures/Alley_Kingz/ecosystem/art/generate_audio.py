#!/usr/bin/env python3
"""
ALLEY KINGZ -- AUDIO GENERATOR (ElevenLabs Music + TTS, pure stdlib)
====================================================================
Generates two asset classes for the game and saves them under game/assets/:

  1. ARENA THEMES  -> assets/music/<arena>.mp3   (instrumental, loop-friendly)
     Eleven Music API: POST /v1/music  (music_length_ms, force_instrumental).
     Falls back to /v1/sound-generation (30s loop bed) if /v1/music is not
     available on the key -- and prints which path it used. Honest, no faking.

  2. VOICE LINES   -> assets/vo/<slug>.mp3       (short gritty war-cry / one-liner)
     TTS API: POST /v1/text-to-speech/{voice_id}  (eleven_multilingual_v2).

RUN:  ELEVENLABS_API_KEY=sk_xxxx python3 generate_audio.py
      python3 generate_audio.py --force        # regen all (else skip existing)
      python3 generate_audio.py --only music   # music only
      python3 generate_audio.py --only vo       # voice only
      python3 generate_audio.py --probe         # confirm endpoints, generate 1 test each
Pure stdlib (urllib/json/os). No pip deps -- runs on the phone.
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

# --- KEY ISOLATION (Alley Kingz must NOT share budget with the other 11Labs projects) ---
# Prefer a DEDICATED Alley Kingz key so the game's audio generation never draws
# down the shared voice-caller / hive-voice / stark_ai budget. Falls back to the
# shared key so this still runs today; the instant you mint a scoped key named
# ALLEY_KINGZ_ELEVENLABS_API_KEY (in 03_Credentials/.env), the game uses it
# automatically with zero code change. See ELEVENLABS_KEY_ISOLATION.md.
def resolve_key():
    for var in ("ALLEY_KINGZ_ELEVENLABS_API_KEY", "AK_ELEVENLABS_API_KEY"):
        v = os.environ.get(var)
        if v:
            return v, var
    v = os.environ.get("ELEVENLABS_API_KEY")
    if v:
        return v, "ELEVENLABS_API_KEY [SHARED -- mint a dedicated AK key, see ELEVENLABS_KEY_ISOLATION.md]"
    return None, None

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.normpath(os.path.join(HERE, "..", "game", "assets", "music"))
VO_DIR = os.path.normpath(os.path.join(HERE, "..", "game", "assets", "vo"))

MUSIC_API = "https://api.elevenlabs.io/v1/music"
SFX_API = "https://api.elevenlabs.io/v1/sound-generation"
TTS_API = "https://api.elevenlabs.io/v1/text-to-speech"
VOICES_API = "https://api.elevenlabs.io/v1/voices"

# Gritty/aggressive preset voice. Default is "Clyde" (war veteran, raspy/intense),
# a stock ElevenLabs voice id. Overridable via AK_VOICE_ID env if the account
# does not expose Clyde. We verify it exists via GET /v1/voices at runtime.
DEFAULT_VOICE_ID = "2EiwWnXFnvU5JabPnv8n"  # Clyde
DEFAULT_VOICE_NAME = "Clyde"

# arena slug -> music prompt. Loop-friendly, no vocals, sits UNDER battle SFX.
ARENAS = {
  "the_lot": (
    "gritty junkyard hip-hop battle instrumental, hard war drums, dirty distorted "
    "electric guitar riff, scrappy underdog street energy, hard-hitting boom-bap, "
    "looping, no vocals, instrumental only"),
  "arena_a_neon_night": (
    "dark cyberpunk synthwave battle pulse, driving arpeggiated synth bass, neon "
    "tension, retro 80s sci-fi combat groove, looping, no vocals, instrumental only"),
  "arena_b_golden_industrial": (
    "heavy industrial rock battle instrumental, clanging metal percussion, distorted "
    "guitar, daytime grind energy, pounding drums, looping, no vocals, instrumental only"),
  "arena_c_rain_docks": (
    "moody dark electronic battle bed, deep sub bass, rain ambience, stormy brooding "
    "tension, slow menacing groove, looping, no vocals, instrumental only"),
}
MUSIC_LEN_MS = 50000  # ~50s loop bed (Eleven Music range 3000-600000)

# voice slug -> spoken line. Short, punchy, gritty cyberpunk war-dog announcer vibe.
VO_LINES = {
  "youre_going_down": "You're going down!",
  "run_with_the_pack": "Run with the pack!",
  "light_em_up": "Light 'em up!",
  "alley_kingz_ride": "Alley Kingz ride!",
  "send_it": "Send it!",
  "crownbreaker": "Crownbreaker!",
  "packs_got_teeth": "Pack's got teeth!",
  "eat_asphalt": "Eat asphalt!",
  "we_own_these_streets": "We own these streets!",
  "bring_the_noise": "Bring the noise!",
  "bcardd_kingly": "Bow to B-Card-D. The dealer always wins.",   # Mythic #0001 line -- phonetic 'B-Card-D' so TTS never voices the old brand name; regen this file
  "faction_taunt": "Wrong alley, runt. This block is ours.",      # faction taunt
}
VOICE_SETTINGS = {"stability": 0.35, "similarity_boost": 0.8, "style": 0.6, "use_speaker_boost": True}


def _post(url, payload, key, timeout=300):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("xi-api-key", key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "audio/mpeg")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def _is_mp3(data):
    return data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def list_voices(key):
    req = urllib.request.Request(VOICES_API, method="GET")
    req.add_header("xi-api-key", key)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  voices list failed:", type(e).__name__, str(e)[:120])
        return None


def resolve_voice(key):
    """Return (voice_id, voice_name) -- env override, else verify default, else
    pick the first gritty-sounding available voice, else first voice."""
    env_id = os.environ.get("AK_VOICE_ID")
    data = list_voices(key)
    if not data or "voices" not in data:
        vid = env_id or DEFAULT_VOICE_ID
        print("  (could not list voices; using %s)" % vid)
        return vid, env_id or DEFAULT_VOICE_NAME
    voices = data["voices"]
    by_id = {v.get("voice_id"): v for v in voices}
    if env_id and env_id in by_id:
        return env_id, by_id[env_id].get("name", "env")
    if DEFAULT_VOICE_ID in by_id:
        return DEFAULT_VOICE_ID, by_id[DEFAULT_VOICE_ID].get("name", DEFAULT_VOICE_NAME)
    # heuristic: prefer a male/intense voice by name/labels
    gritty_kw = ("clyde", "arnold", "callum", "harry", "drew", "dave", "antoni", "josh")
    for v in voices:
        nm = (v.get("name") or "").lower()
        if any(k in nm for k in gritty_kw):
            print("  default voice not on key; using gritty match:", v.get("name"))
            return v.get("voice_id"), v.get("name")
    print("  default voice not on key; using first available:", voices[0].get("name"))
    return voices[0].get("voice_id"), voices[0].get("name")


# ----- MUSIC -------------------------------------------------------------
_MUSIC_MODE = None  # cached: "music" | "sfx"

def music_endpoint_mode(key):
    """Confirm whether /v1/music works on this key. Cached after first probe."""
    global _MUSIC_MODE
    if _MUSIC_MODE:
        return _MUSIC_MODE
    payload = {"prompt": "short instrumental test, hard war drums",
               "music_length_ms": 10000, "force_instrumental": True}
    try:
        data, ct = _post(MUSIC_API, payload, key, timeout=300)
        if _is_mp3(data):
            _MUSIC_MODE = "music"
            print("  [endpoint] /v1/music AVAILABLE (mp3 %d bytes, ct=%s)" % (len(data), ct))
            return _MUSIC_MODE
        print("  [endpoint] /v1/music returned non-mp3:", data[:60])
    except urllib.error.HTTPError as e:
        print("  [endpoint] /v1/music UNAVAILABLE HTTP", e.code,
              e.read().decode("utf-8", "replace")[:200])
    except Exception as e:
        print("  [endpoint] /v1/music error:", type(e).__name__, str(e)[:160])
    _MUSIC_MODE = "sfx"
    print("  [endpoint] FALLBACK -> /v1/sound-generation 30s loop bed")
    return _MUSIC_MODE


def gen_music(slug, prompt, key, force):
    out = os.path.join(MUSIC_DIR, slug + ".mp3")
    if os.path.exists(out) and not force:
        print("  skip (exists):", slug); return "skip"
    mode = music_endpoint_mode(key)
    try:
        if mode == "music":
            data, _ = _post(MUSIC_API, {"prompt": prompt, "music_length_ms": MUSIC_LEN_MS,
                                        "force_instrumental": True}, key)
        else:
            data, _ = _post(SFX_API, {"text": prompt, "duration_seconds": 30,
                                      "loop": True, "prompt_influence": 0.4}, key)
    except urllib.error.HTTPError as e:
        print("  FAIL", slug, "HTTP", e.code, e.read().decode("utf-8", "replace")[:160])
        return "fail"
    except Exception as e:
        print("  FAIL", slug, type(e).__name__, str(e)[:160]); return "fail"
    if not _is_mp3(data):
        print("  WARN", slug, "not mp3:", data[:40]); return "fail"
    with open(out, "wb") as fh:
        fh.write(data)
    print("  saved:", slug, "(%d bytes, %s)" % (len(data), mode)); return "made"


# ----- VOICE -------------------------------------------------------------
def gen_vo(slug, line, voice_id, key, force):
    out = os.path.join(VO_DIR, slug + ".mp3")
    if os.path.exists(out) and not force:
        print("  skip (exists):", slug); return "skip"
    url = "%s/%s" % (TTS_API, voice_id)
    payload = {"text": line, "model_id": "eleven_multilingual_v2",
               "voice_settings": VOICE_SETTINGS}
    try:
        data, _ = _post(url, payload, key, timeout=120)
    except urllib.error.HTTPError as e:
        print("  FAIL", slug, "HTTP", e.code, e.read().decode("utf-8", "replace")[:160])
        return "fail"
    except Exception as e:
        print("  FAIL", slug, type(e).__name__, str(e)[:160]); return "fail"
    if not _is_mp3(data):
        print("  WARN", slug, "not mp3:", data[:40]); return "fail"
    with open(out, "wb") as fh:
        fh.write(data)
    print("  saved:", slug, "(%d bytes) \"%s\"" % (len(data), line)); return "made"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", choices=["music", "vo"], default=None)
    ap.add_argument("--probe", action="store_true", help="confirm endpoints + 1 test each")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    key, key_var = resolve_key()
    if not key:
        print("No key. Set ALLEY_KINGZ_ELEVENLABS_API_KEY (preferred) or "
              "ELEVENLABS_API_KEY in 03_Credentials/.env and re-run."); return 0
    print("[key] using", key_var, "(...%s)" % key[-6:])
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(VO_DIR, exist_ok=True)

    if args.probe:
        print("== PROBE: music endpoint ==")
        mode = music_endpoint_mode(key)
        print("music mode =", mode)
        print("== PROBE: voice ==")
        vid, vname = resolve_voice(key)
        print("voice =", vname, vid)
        r = gen_vo("_probe", "Alley Kingz ride!", vid, key, force=True)
        print("vo probe =", r)
        return 0

    made = skip = fail = 0
    if args.only in (None, "music"):
        print("== ARENA THEMES (music) ==")
        items = list(ARENAS.items())
        for i, (slug, prompt) in enumerate(items, 1):
            print("[%d/%d]" % (i, len(items)), slug)
            r = gen_music(slug, prompt, key, args.force)
            made += r == "made"; skip += r == "skip"; fail += r == "fail"
            if i < len(items): time.sleep(args.delay)

    if args.only in (None, "vo"):
        print("\n== VOICE LINES (TTS) ==")
        vid, vname = resolve_voice(key)
        print("  voice:", vname, "(%s)" % vid)
        items = list(VO_LINES.items())
        for i, (slug, line) in enumerate(items, 1):
            print("[%d/%d]" % (i, len(items)), slug)
            r = gen_vo(slug, line, vid, key, args.force)
            made += r == "made"; skip += r == "skip"; fail += r == "fail"
            if i < len(items): time.sleep(args.delay)

    print("\nDone. made=%d skip=%d fail=%d" % (made, skip, fail))
    print("  music -> %s" % MUSIC_DIR)
    print("  vo    -> %s" % VO_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
