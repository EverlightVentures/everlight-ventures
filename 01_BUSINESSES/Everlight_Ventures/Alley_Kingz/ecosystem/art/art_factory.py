#!/usr/bin/env python3
"""
ALLEY KINGZ -- UNIFIED ART FACTORY (one queue, one cron, free-first Leonardo)
============================================================================
THE standing pipeline (operator law 2026-06-07): anything that needs custom art
and currently shows a placeholder is auto-painted. One prioritized drainer over
ALL sources so the free Leonardo daily cap is spent coherently (not split across
3 competing crons). A placeholder is always temporary.

SOURCES (priority order):
  1. AD-HOC QUEUE  `_state/ak_art_queue.json`  -- any new item (shop product, etc.)
     appended via `--enqueue`. [{id, prompt, negative, out, w, h}]
  2. CARDS         `data/card_art_manifest.json` entries whose art is not on disk (new-first)
  3. MAPS          the 10-city x 10-level x 4-district set (imported from generate_world_maps)

RUN:   LEONARDO_API_KEY=xxx python3 art_factory.py --limit 12
ENQUEUE: python3 art_factory.py --enqueue --id shop_chest_crew --prompt "<gritty prompt>" --out game/assets/cards/chest_crew.png
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ECO  = os.path.normpath(os.path.join(HERE, ".."))
ROOT = "/mnt/sdcard/AA_MY_DRIVE"
QUEUE = os.path.join(ROOT, "_state", "ak_art_queue.json")
CARD_MANIFEST = os.path.join(ECO, "data", "card_art_manifest.json")
LEO = "https://cloud.leonardo.ai/api/rest/v1"; LEO_MODEL = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"
# The house art voice -- gritty TV-MA street / Twisted-Metal, appended to ad-hoc prompts.
GRITTY = ("gritty TV-MA street aesthetic, cyberpunk dog-crew / Twisted-Metal, chrome + rust + neon grime, "
          "Everlight gold #D4AF37 on vanta-black #050507, premium, NOT kiddish, NOT cartoonish")

def _bytes(u, t=180):
    r = urllib.request.Request(u); r.add_header("User-Agent", "Mozilla/5.0")
    return urllib.request.urlopen(r, timeout=t).read()

def leo_gen(prompt, neg, w, h, key):
    hd = {"Authorization": "Bearer " + key, "Accept": "application/json", "Content-Type": "application/json"}
    body = {"prompt": prompt, "modelId": LEO_MODEL, "width": w, "height": h, "num_images": 1, "alchemy": True, "public": False}
    if neg: body["negative_prompt"] = neg
    req = urllib.request.Request(LEO + "/generations", data=json.dumps(body).encode(), method="POST")
    for k, v in hd.items(): req.add_header(k, v)
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError("gen %d: %s" % (e.code, e.read().decode()[:120]))  # surface the body (e.g. "not enough api tokens")
    gid = (resp.get("sdGenerationJob") or {}).get("generationId")
    if not gid: raise RuntimeError("no gen id")
    for _ in range(60):
        time.sleep(3)
        rq = urllib.request.Request(LEO + "/generations/" + gid)
        for k, v in hd.items(): rq.add_header(k, v)
        try: g = (json.loads(urllib.request.urlopen(rq, timeout=60).read()).get("generations_by_pk") or {})
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503): continue
            raise
        if g.get("status") == "COMPLETE":
            im = g.get("generated_images") or []
            if im and im[0].get("url"): return _bytes(im[0]["url"])
            raise RuntimeError("complete no url")
        if g.get("status") == "FAILED": raise RuntimeError("FAILED")
    raise RuntimeError("timeout")

def resolve(p):
    if os.path.isabs(p): return p
    if p.startswith("game/") or p.startswith("assets/") or p.startswith("data/"): return os.path.join(ECO, p)
    return os.path.join(ECO, "game", "assets", "cards", p)

def worklist():
    """Build the missing-art work list, priority: queue -> cards(new-first) -> maps."""
    jobs = []
    # 1. ad-hoc queue
    if os.path.exists(QUEUE):
        for q in json.load(open(QUEUE)):
            jobs.append((q["id"], q["prompt"], q.get("negative", ""), resolve(q["out"]), q.get("w", 768), q.get("h", 768)))
    # 2. cards
    if os.path.exists(CARD_MANIFEST):
        cards = json.load(open(CARD_MANIFEST)); cards = cards if isinstance(cards, list) else cards.get("cards", cards)
        cards.sort(key=lambda c: (not c.get("is_new"), c.get("cardNumber", "")))
        for c in cards:
            out = resolve(c.get("art_path") or ("game/assets/cards/%s.png" % c.get("slug")))
            jobs.append((c.get("slug"), c.get("prompt", ""), c.get("negative_prompt", ""), out, 768, 768))
    # 3. maps (import the world-map definitions)
    try:
        sys.path.insert(0, HERE); import generate_world_maps as gwm
        for slug, theme, _r in gwm.ARENAS:
            for lvl in range(1, 11):
                for dslug, drole in gwm.DISTRICTS:
                    out = os.path.join(gwm.MAPS_DIR, slug, "L%02d_%s.png" % (lvl, dslug))
                    prompt = "%s A %s, showing %s, %s. %s" % (gwm.FRAMING, theme, drole, gwm.LEVEL_MODS[lvl-1], gwm.NEG)
                    jobs.append(("map_%s_L%02d_%s" % (slug, lvl, dslug), prompt, gwm.NEG, out, gwm.ARENA_W, gwm.ARENA_H))
    except Exception as e:
        print("  (maps source unavailable: %s)" % str(e)[:60])
    # de-dupe by out path, keep first (priority); drop already-painted
    seen = set(); out_jobs = []
    for j in jobs:
        if j[3] in seen: continue
        seen.add(j[3])
        if not os.path.exists(j[3]) or os.path.getsize(j[3]) == 0: out_jobs.append(j)  # 0-byte = a prior failure stub, re-paint it
    return out_jobs

def enqueue(a):
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    q = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    prompt = a.prompt if a.prompt.strip().endswith(GRITTY) else (a.prompt.rstrip(". ") + ". " + GRITTY)
    q = [x for x in q if x.get("id") != a.id]  # replace same id
    q.append({"id": a.id, "prompt": prompt, "negative": a.neg, "out": a.out, "w": a.w, "h": a.h})
    json.dump(q, open(QUEUE, "w"), indent=2)
    print("enqueued:", a.id, "->", a.out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--id"); ap.add_argument("--prompt", default=""); ap.add_argument("--out", default="")
    ap.add_argument("--neg", default=""); ap.add_argument("--w", type=int, default=768); ap.add_argument("--h", type=int, default=768)
    a = ap.parse_args()
    if a.enqueue:
        if not (a.id and a.prompt and a.out): print("need --id --prompt --out"); return 2
        enqueue(a); return 0
    key = os.environ.get("LEONARDO_API_KEY")
    if not key: print("no LEONARDO_API_KEY"); return 2
    jobs = worklist()
    print("art_factory: %d assets need painting" % len(jobs))
    made = fail = streak = 0
    for jid, prompt, neg, out, w, h in jobs:
        if a.limit and made >= a.limit: print("-- hit --limit %d --" % a.limit); break
        try:
            data = leo_gen(prompt, neg, w, h, key)
            if not data: raise RuntimeError("empty image")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f: f.write(data)   # write ONLY on real bytes -- never leave a 0-byte stub
            made += 1; streak = 0
            print("  PAINTED", jid)
        except Exception as e:
            msg = str(e); print("  FAIL", jid, msg[:80]); fail += 1; streak += 1
            # Daily free-token exhaustion (400 "not enough api tokens") or rate cap
            # won't clear mid-batch: stop fast instead of churning the whole worklist.
            if "not enough api tokens" in msg or "gen 400" in msg or "429" in msg:
                print("  -- Leonardo tokens exhausted; stopping until UTC reset --"); break
            if streak >= 3:
                print("  -- %d consecutive failures; aborting batch --" % streak); break
        time.sleep(a.delay)
    print("\nDONE made=%d fail=%d  | %d still need art" % (made, fail, max(0, len(jobs) - made)))
    return 0

if __name__ == "__main__": sys.exit(main())
