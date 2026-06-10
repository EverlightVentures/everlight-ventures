#!/usr/bin/env python3
"""
ALLEY KINGZ -- CARD ART FACTORY (reads card_art_manifest.json, pure stdlib)
==========================================================================
Paints the 106-card roster (58 new variants first) from the workflow's manifest,
gritty TV-MA prompts. Idempotent + batchable + self-retiring via the cron.
RUN: LEONARDO_API_KEY=xxx python3 generate_card_art.py --limit 12
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ECO = os.path.normpath(os.path.join(HERE, ".."))
MANIFEST = os.path.join(ECO, "data", "card_art_manifest.json")
SIZE = 768
LEO = "https://cloud.leonardo.ai/api/rest/v1"; LEO_MODEL = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"

def _bytes(u, t=180):
    r = urllib.request.Request(u); r.add_header("User-Agent", "Mozilla/5.0")
    return urllib.request.urlopen(r, timeout=t).read()

def leo_gen(prompt, neg, key):
    h = {"Authorization": "Bearer " + key, "Accept": "application/json", "Content-Type": "application/json"}
    body = {"prompt": prompt, "modelId": LEO_MODEL, "width": SIZE, "height": SIZE, "num_images": 1, "alchemy": True, "public": False}
    if neg: body["negative_prompt"] = neg
    req = urllib.request.Request(LEO + "/generations", data=json.dumps(body).encode(), method="POST")
    for k, v in h.items(): req.add_header(k, v)
    gid = (json.loads(urllib.request.urlopen(req, timeout=120).read()).get("sdGenerationJob") or {}).get("generationId")
    if not gid: raise RuntimeError("no gen id")
    for _ in range(60):
        time.sleep(3)
        rq = urllib.request.Request(LEO + "/generations/" + gid)
        for k, v in h.items(): rq.add_header(k, v)
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

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true"); ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args()
    key = os.environ.get("LEONARDO_API_KEY")
    if not key: print("no LEONARDO_API_KEY"); return 2
    cards = json.load(open(MANIFEST))
    cards = cards if isinstance(cards, list) else cards.get("cards", cards)
    cards.sort(key=lambda c: (not c.get("is_new"), c.get("cardNumber", "")))  # new first
    made = skip = fail = 0
    for c in cards:
        ap_rel = c.get("art_path") or ("game/assets/cards/%s.png" % c.get("slug"))
        out = os.path.join(ECO, ap_rel)
        if a.limit and made >= a.limit: print("-- hit --limit %d --" % a.limit); break
        if os.path.exists(out) and not a.force: skip += 1; continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            png = leo_gen(c.get("prompt", ""), c.get("negative_prompt", ""), key)
            open(out, "wb").write(png); made += 1
            print("  CARD %s %s (%s/%s)" % (c.get("cardNumber"), c.get("slug"), c.get("rarity"), c.get("variant")))
        except Exception as e:
            print("  FAIL %s: %s" % (c.get("slug"), str(e)[:70])); fail += 1
        time.sleep(a.delay)
    total = len([c for c in cards])
    have = len([c for c in cards if os.path.exists(os.path.join(ECO, c.get("art_path") or ""))])
    print("\nDONE made=%d skip=%d fail=%d  | painted %d/%d cards" % (made, skip, fail, have, total))
    return 0

if __name__ == "__main__": sys.exit(main())
