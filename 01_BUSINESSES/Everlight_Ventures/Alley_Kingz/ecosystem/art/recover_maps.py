#!/usr/bin/env python3
# Recover already-generated maps from the Leonardo gallery (tokens already spent).
# The generator truncated local files to 0 bytes before downloading, so download
# failures left empties -- but the images COMPLETED on Leonardo. Re-download them,
# mapping each prompt back to its city/level/district via the script's own constants.
import urllib.request, json, os, sys, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_world_maps as gwm

key = os.environ["LEONARDO_API_KEY"]
uid = "b0700833-9b45-44e8-b28d-2da6587a5553"
LEO = "https://cloud.leonardo.ai/api/rest/v1"
h = {"Authorization": "Bearer " + key, "Accept": "application/json"}

themes = [(t, s) for s, t, _ in gwm.ARENAS]
droles = [(d, ds) for ds, d in gwm.DISTRICTS]
levs   = list(enumerate(gwm.LEVEL_MODS))   # (idx, modtext); level = idx+1

def gens(off):
    u = LEO + "/generations/user/%s?offset=%d&limit=50" % (uid, off)
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=45).read()).get("generations") or []

def dl(url):
    rq = urllib.request.Request(url); rq.add_header("User-Agent", "Mozilla/5.0")
    return urllib.request.urlopen(rq, timeout=120).read()

allg = []
for off in (0, 50, 100, 150, 200, 250, 300):
    g = gens(off)
    if not g: break
    allg += g
print("total gallery gens fetched:", len(allg))

rec = have = unm = 0
for g in allg:
    if g.get("status") != "COMPLETE": continue
    im = g.get("generated_images") or []
    if not im or not im[0].get("url"): continue
    p = g.get("prompt") or ""
    if "Clash-Royale" not in p: continue                       # map prompts only
    city = next((s for t, s in themes if t and t in p), None)
    dist = next((ds for d, ds in droles if d and d in p), None)
    lvl  = next((i + 1 for i, m in levs if m and m in p), None)
    if not (city and dist and lvl): unm += 1; continue
    out = os.path.join(gwm.MAPS_DIR, city, "L%02d_%s.png" % (lvl, dist))
    if os.path.exists(out) and os.path.getsize(out) > 20000: have += 1; continue
    try:
        b = dl(im[0]["url"])
        if len(b) > 20000:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").write(b); rec += 1
            print("REC %-18s L%02d %-7s %dKB" % (city, lvl, dist, len(b)//1024))
        else:
            print("tiny dl %s L%02d %s (%dB)" % (city, lvl, dist, len(b)))
    except Exception as e:
        print("dlfail %s L%02d %s: %s" % (city, lvl, dist, str(e)[:40]))
print("RECOVERED=%d  already-valid=%d  unmapped=%d" % (rec, have, unm))
