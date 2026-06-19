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
import os, sys, json, time, base64, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ECO  = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.environ.get("AK_ROOT", "/mnt/sdcard/AA_MY_DRIVE")  # override on e5 / any host
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

CF_ACCT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "d06376317522c7451e390a9af44aebba")
CF_AI = "https://api.cloudflare.com/client/v4/accounts/%s/ai/run/" % CF_ACCT

def cf_gen(prompt, neg, w, h, tok):
    # Cloudflare Workers AI -- 10k free neurons/day (~100+ images), no renewal cliff.
    # flux-1-schnell is square-only JSON+b64; SDXL takes width/height and returns raw PNG.
    if w == h:
        model = "@cf/black-forest-labs/flux-1-schnell"
        body = {"prompt": (prompt + (" . avoid: " + neg if neg else ""))[:2040], "steps": 8}
    else:
        model = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
        body = {"prompt": prompt[:2040], "width": w, "height": h, "num_steps": 20}
        if neg: body["negative_prompt"] = neg[:2040]
    req = urllib.request.Request(CF_AI + model, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + tok); req.add_header("Content-Type", "application/json")
    try:
        raw = urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("cf %d: %s" % (e.code, e.read().decode()[:120]))
    if raw[:1] == b"{":
        j = json.loads(raw)
        img = (j.get("result") or {}).get("image")
        if not img: raise RuntimeError("cf no image: " + str(j.get("errors"))[:100])
        return base64.b64decode(img)
    return raw

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

def _is_map(jid):
    return str(jid).startswith("map_")


def _apply_lane(jobs, lane):
    """Alternate the daily focus -- cards one day, maps the next (50/50) -- so BOTH
    keep flowing into the game evenly instead of finishing all cards before any maps.
    'auto' picks the lane by UTC day-of-year parity (even=cards, odd=maps).
    If the chosen lane is already fully painted, spend the day on the other one."""
    if lane == "auto":
        import datetime
        doy = datetime.datetime.now(datetime.timezone.utc).timetuple().tm_yday
        lane = "cards" if doy % 2 == 0 else "maps"
        print("  lane=auto -> '%s' (UTC day-of-year %d)" % (lane, doy))
    if lane not in ("cards", "maps"):
        return jobs
    want_map = (lane == "maps")
    laned = [j for j in jobs if _is_map(j[0]) == want_map]
    if not laned:
        print("  '%s' lane fully painted -> working the other lane today" % lane)
        return jobs
    print("  lane '%s': %d of %d outstanding assets" % (lane, len(laned), len(jobs)))
    return laned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--enqueue", action="store_true")
    ap.add_argument("--id"); ap.add_argument("--prompt", default=""); ap.add_argument("--out", default="")
    ap.add_argument("--neg", default=""); ap.add_argument("--w", type=int, default=768); ap.add_argument("--h", type=int, default=768)
    ap.add_argument("--lane", choices=["all", "cards", "maps", "auto"], default="all")
    a = ap.parse_args()
    if a.enqueue:
        if not (a.id and a.prompt and a.out): print("need --id --prompt --out"); return 2
        enqueue(a); return 0
    # Engine failover chain. Leonardo API credits are PURCHASED (no daily reset --
    # verified 2026-06-10: apiPaidTokens=21, renewal=null), so when they run dry the
    # batch fails over to Cloudflare Workers AI (CF_AI_TOKEN, 10k free neurons/day)
    # instead of waiting for a reset that never comes.
    leo_key = os.environ.get("LEONARDO_API_KEY")
    cf_tok  = os.environ.get("CF_AI_TOKEN")
    engines = [e for e, k in (("leo", leo_key), ("cf", cf_tok)) if k]
    if not engines: print("no art engine keys (set LEONARDO_API_KEY and/or CF_AI_TOKEN)"); return 2
    jobs = worklist()
    jobs = _apply_lane(jobs, a.lane)
    print("art_factory: %d assets need painting (engines: %s)" % (len(jobs), "+".join(engines)))
    made = fail = streak = 0
    for jid, prompt, neg, out, w, h in jobs:
        if a.limit and made >= a.limit: print("-- hit --limit %d --" % a.limit); break
        if not engines: break
        try:
            data = None
            while engines:
                eng = engines[0]
                try:
                    data = leo_gen(prompt, neg, w, h, leo_key) if eng == "leo" else cf_gen(prompt, neg, w, h, cf_tok)
                    break
                except Exception as e:
                    msg = str(e)
                    # exhausted/unauthorized engines won't recover mid-batch: drop and fail over
                    leo_dead = eng == "leo" and ("not enough api tokens" in msg or "gen 400" in msg or "429" in msg)
                    cf_dead  = eng == "cf"  and any(s in msg for s in ("cf 401", "cf 403", "cf 429", "capacity"))
                    if leo_dead or cf_dead:
                        print("  -- engine %s down (%s); failing over --" % (eng, msg[:70]))
                        engines.pop(0); continue
                    raise
            if not engines:
                print("  -- all art engines exhausted; stopping batch --"); fail += 1; break
            if not data: raise RuntimeError("empty image")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f: f.write(data)   # write ONLY on real bytes -- never leave a 0-byte stub
            made += 1; streak = 0
            print("  PAINTED %s (via %s)" % (jid, engines[0]))
        except Exception as e:
            msg = str(e); print("  FAIL", jid, msg[:80]); fail += 1; streak += 1
            if streak >= 3:
                print("  -- %d consecutive failures; aborting batch --" % streak); break
        time.sleep(a.delay)
    print("\nDONE made=%d fail=%d  | %d still need art" % (made, fail, max(0, len(jobs) - made)))
    return 0

if __name__ == "__main__": sys.exit(main())
