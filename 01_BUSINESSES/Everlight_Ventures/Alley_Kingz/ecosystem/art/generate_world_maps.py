#!/usr/bin/env python3
"""
ALLEY KINGZ -- WORLD MAP FACTORY (400-map pipeline, pure stdlib)
===============================================================
10 ARENAS (cities) x 10 LEVELS x 4 DISTRICT MAPS = 400 unique battlefields,
+ per-arena music. Data-driven: each map's prompt = city theme + district +
per-level intensity shift (so a city's 10 levels look like a journey deeper in).
Batchable + idempotent (skips existing). Free Leonardo tier is ~10-15 imgs/day,
so run in batches (--arena / --limit); a paid tier (~$8 total) does all 400 fast.

RUN (one city at a time, friendly to the free daily cap):
  LEONARDO_API_KEY=xxx python3 generate_world_maps.py --arena the_lot
  LEONARDO_API_KEY=xxx python3 generate_world_maps.py --limit 12        # next 12 missing
  ELEVENLABS_API_KEY=sk_ python3 generate_world_maps.py --music-only    # the 10 city themes
OUTPUT:
  game/assets/maps/<arena>/L<NN>_<district>.png   (400)
  game/assets/music/<arena>.mp3                   (10 city themes; the 4 originals already exist)
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.normpath(os.path.join(HERE, "..", "game"))
MAPS_DIR = os.path.join(GAME, "assets", "maps")
MUSIC_DIR = os.path.join(GAME, "assets", "music")
ARENA_W, ARENA_H = 832, 1216

# ---- The 10 cities (junkyard -> empire). 4 already have arena art/music. ----
ARENAS = [
  ("the_lot",          "a gritty rusted junkyard scrap-lot, stacks of wrecked cars + chain-link, rust-brown",      "humble starting slum"),
  ("neon_night",       "a wet cyberpunk neon downtown, glowing storefronts + skyscrapers, cyan + magenta neon",     "electric city core"),
  ("golden_industrial","a golden-hour warehouse industrial yard, corrugated steel + shipping containers, amber",    "working district"),
  ("rain_docks",       "a neon harbor dock in the rain at night, wet planked piers + cargo cranes, teal + gold",     "stormy waterfront"),
  ("undercity_subway", "an abandoned neon subway + underground transit tunnels, flickering tube lights, grimy tile", "the underbelly"),
  ("skyline_rooftops", "high-rise rooftops above the city at dawn, helipads + skyline + antennae, pink-gold sky",    "the heights"),
  ("toxic_sewers",     "toxic green chemical sewers + waste tunnels, hazard glow + dripping pipes, sickly green",    "the poison works"),
  ("casino_strip",     "a neon casino strip boulevard at night, gold marquee lights + slot glow, vegas opulence",    "the gambling row"),
  ("frost_district",   "a frozen ice-bound district, snow drifts + blue ice + cold neon, frostbitten metal",        "the deep freeze"),
  ("crown_citadel",    "the Empire crown citadel, a golden imperial throne-city of gilded towers, regal gold",       "the final throne"),
]
# the 4 convoy stops crossed each match (themed per city by the prompt)
DISTRICTS = [("gate", "the entrance gate district"), ("market", "the crowded market strip"),
             ("works", "the heavy industrial works"), ("core", "the heart / boss core")]
# per-level shift (1..10): the city escalates as you climb its 10 levels
LEVEL_MODS = [
  "calm clear daylight, peaceful", "overcast hazy afternoon", "warm dusk, long shadows",
  "early night, lights on", "thick fog rolling in", "light rain, wet reflections",
  "heavy storm, lightning", "smoke + embers drifting", "neon overload, oversaturated glow",
  "apocalyptic red sky, ruined and intense",
]
FRAMING = ("Top-down slight-angle Clash-Royale-style battle board, vertical portrait, two clear vertical "
           "combat lanes split by a central divider with two side bridges, three tower pads per side, gold "
           "#D4AF37 tower pads + lane edges, hyper-real PBR environment (Uncharted 4 fidelity), readable "
           "uncluttered lanes, cinematic lighting, vanta-black #050507 shadow.")
NEG = "no characters, no units, no UI, no text, no watermark, low quality, blurry, flat 2d."
MUSIC_MOODS = {  # for the 6 new cities (the 4 originals already have tracks)
  "undercity_subway":"a dark gritty underground subway battle loop, echoing industrial percussion + bass, tense",
  "skyline_rooftops":"a soaring high-altitude rooftop battle loop, epic synth + driving beat, triumphant heights",
  "toxic_sewers":"a murky toxic-sewer battle loop, dripping ambience + distorted bass, dangerous + sickly",
  "casino_strip":"a glitzy neon-casino battle loop, swaggy jazzy hip-hop beat + slot chimes, high-roller energy",
  "frost_district":"a frozen ice-district battle loop, crystalline cold synths + heavy beat, chilling tension",
  "crown_citadel":"an epic imperial final-boss throne battle loop, grand orchestral + trap drums, regal climax",
}
LEO = "https://cloud.leonardo.ai/api/rest/v1"; LEO_MODEL = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"

def _bytes(u,t=180):
    r=urllib.request.Request(u); r.add_header("User-Agent","Mozilla/5.0")
    return urllib.request.urlopen(r,timeout=t).read()

def leo_gen(prompt, key):
    h={"Authorization":"Bearer "+key,"Accept":"application/json","Content-Type":"application/json"}
    body={"prompt":prompt,"modelId":LEO_MODEL,"width":ARENA_W,"height":ARENA_H,"num_images":1,"alchemy":True,"public":False,"negative_prompt":NEG}
    req=urllib.request.Request(LEO+"/generations",data=json.dumps(body).encode(),method="POST")
    for k,v in h.items(): req.add_header(k,v)
    gid=(json.loads(urllib.request.urlopen(req,timeout=120).read()).get("sdGenerationJob") or {}).get("generationId")
    if not gid: raise RuntimeError("no gen id")
    for _ in range(60):
        time.sleep(3)
        rq=urllib.request.Request(LEO+"/generations/"+gid)
        for k,v in h.items(): rq.add_header(k,v)
        try: g=(json.loads(urllib.request.urlopen(rq,timeout=60).read()).get("generations_by_pk") or {})
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503): continue
            raise
        if g.get("status")=="COMPLETE":
            im=g.get("generated_images") or []
            if im and im[0].get("url"): return _bytes(im[0]["url"])
            raise RuntimeError("complete no url")
        if g.get("status")=="FAILED": raise RuntimeError("FAILED")
    raise RuntimeError("timeout")

def music_gen(mood, key, secs=45):
    body=json.dumps({"prompt":mood,"music_length_ms":secs*1000}).encode()
    req=urllib.request.Request("https://api.elevenlabs.io/v1/music",data=body,method="POST")
    req.add_header("xi-api-key",key); req.add_header("Content-Type","application/json")
    data=urllib.request.urlopen(req,timeout=180).read()
    if data[:3] not in (b"ID3",b"\xff\xfb",b"\xff\xf3"): raise RuntimeError("not mp3: "+data[:60].decode("utf-8","replace"))
    return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--arena"); ap.add_argument("--limit",type=int,default=0)
    ap.add_argument("--music-only",action="store_true"); ap.add_argument("--maps-only",action="store_true")
    ap.add_argument("--force",action="store_true"); ap.add_argument("--delay",type=float,default=2.0)
    a=ap.parse_args()
    leo=os.environ.get("LEONARDO_API_KEY"); el=os.environ.get("ELEVENLABS_API_KEY")
    made=skip=fail=0
    # ---- MUSIC (10 city themes; 4 originals already exist as the_lot/neon/industrial/docks loops) ----
    if not a.maps_only and el:
        os.makedirs(MUSIC_DIR,exist_ok=True)
        for slug,mood in MUSIC_MOODS.items():
            if a.arena and slug!=a.arena: continue
            out=os.path.join(MUSIC_DIR,slug+".mp3")
            if os.path.exists(out) and not a.force: print(" skip music",slug); skip+=1; continue
            try: open(out,"wb").write(music_gen(mood,el)); print(" MUSIC",slug); made+=1
            except Exception as e: print(" FAIL music",slug,str(e)[:80]); fail+=1
            time.sleep(a.delay)
    # ---- MAPS (400) ----
    if not a.music_only and leo:
        for slug,theme,_role in ARENAS:
            if a.arena and slug!=a.arena: continue
            adir=os.path.join(MAPS_DIR,slug); os.makedirs(adir,exist_ok=True)
            for lvl in range(1,11):
                for dslug,drole in DISTRICTS:
                    if a.limit and made>=a.limit: print("\n-- hit --limit %d --"%a.limit); _done(made,skip,fail); return 0
                    out=os.path.join(adir,"L%02d_%s.png"%(lvl,dslug))
                    if os.path.exists(out) and not a.force: skip+=1; continue
                    prompt="%s A %s, showing %s, %s. %s" % (FRAMING, theme, drole, LEVEL_MODS[lvl-1], NEG)
                    try:
                        _d = leo_gen(prompt,leo)                       # AK-FIX: build bytes FIRST -- never open(wb)/truncate on failure
                        if _d and len(_d) > 20000:                     # only write a REAL image (>20KB); empties were the old corrupt-file bug
                            open(out,"wb").write(_d); print(" MAP %s L%02d %s"%(slug,lvl,dslug)); made+=1
                        else: print(" FAIL %s L%02d %s: empty/small (%d B)"%(slug,lvl,dslug,len(_d or b""))); fail+=1
                    except Exception as e: print(" FAIL %s L%02d %s: %s"%(slug,lvl,dslug,str(e)[:70])); fail+=1
                    time.sleep(a.delay)
    elif not a.music_only and not leo: print(" (no LEONARDO_API_KEY -> maps skipped)")
    _done(made,skip,fail); return 0

def _done(m,s,f): print("\nDONE made=%d skip=%d fail=%d  (total target 400 maps + 6 new city tracks)"%(m,s,f))

if __name__=="__main__": sys.exit(main())
