#!/usr/bin/env python3
"""
Alley Kingz -- the ONE ordered generation manifest.

Collapses all four prompt sources into a single spend-ordered list so the whole
3D migration fires from one file, in priority order, with a hard running credit
total the batch runner caps against.

Sources:
  prompts.json         106 dogs   (build_hero_prompts.py, A-pose locked)
  rig_bible.json        20 rigs    (the car-DNA characters, the ONE rig source)
  asset_prompts.json   271 assets  (accessories, chests, crowns, buildings, bosses)
  weapon_prompts.json   88 weapons + attachments

ORDER = risk-first and dependency-first:
  0 PILOT   one of every TYPE, meshed + eyeballed BEFORE the batch commits. The
            gate-before-spend rule applied to money: prove the pipeline on ~6
            assets before trusting it with thousands of credits.
  1 DOGS    the roster is the game. Heroes (Mythic+Legendary) premium, rest standard.
  2 RIGS    showpieces, premium.
  3 WEAPONS held + mounted.
  4 ATTACH  the gunsmith.
  5 CHESTS/CROWNS  the reward moment (juice.js already wired to these).
  6 BUILDINGS      the 4 archetypes x tiers (the 406MB "maps" mirage -> ~12 meshes).
  7 BOSSES/HANDLERS
  8 ACCESSORIES    the money layer (8 slots).
  9 LANDMARKS      Docks + Undercity, so the 38 homeless dogs get turf.
 10 PROPS          catch-all for any future ungrouped asset. Currently EMPTY:
                   every live group has an explicit APH row. It used to hold the
                   20 duplicate rigs (see AK-RIGDEDUP below), which is the only
                   reason it ever looked populated.

MODE: every row is text_to_model by default (we have prompts, the free reference
images are an optional upgrade per asset -- when a gated contract-passing image
exists at art/refs/<id>.png the runner switches that row to image_to_model, which
is higher fidelity). So the pipeline runs today from prompts alone, and each asset
can be upgraded to image-first without re-plumbing.

Read-only on the sources. Writes one manifest.
"""
import json, collections
from pathlib import Path

HERE = Path(__file__).parent

def load(name):
    p = HERE / name
    return json.loads(p.read_text()) if p.exists() else None

def main():
    rows = []

    def add(order, phase, aid, group, prompt, credits, tier, mode="text"):
        rows.append({"order": order, "phase": phase, "id": aid, "group": group,
                     "credits": credits, "tier": tier, "mode": mode,
                     "prompt": prompt})

    dogs = load("prompts.json")
    rigs = load("rig_bible.json")
    assets = load("asset_prompts.json")
    weps = load("weapon_prompts.json")

    HERO = {"Mythic", "Legendary"}

    # 1 DOGS
    for d in (dogs["prompts"] if dogs else []):
        hero = d["rarity"] in HERO
        add(1, "dogs", "dog_" + d["cardNumber"], "dog", d["prompt"],
            55 if hero else 20, "hero" if hero else "standard")

    # 2 RIGS
    for r in (rigs["rigs"] if rigs else []):
        add(2, "rigs", r["id"], "rig", r.get("prompt", ""), 55, "hero")

    # 3-10 assets, grouped
    APH = {"weapon_held": (3, "weapons"), "weapon_mounted": (3, "weapons"),
           "attachment": (4, "attachments"), "chest": (5, "reward"), "crown": (5, "reward"),
           "building": (6, "buildings"), "boss": (7, "bosses"), "handler": (7, "bosses"),
           "accessory": (8, "accessories"), "landmark": (9, "landmarks")}
    # AK-RIGDEDUP 2026-07-18: rig_bible.json is the ONE rig source. asset_prompts.json
    # also ships the same 20 vehicles as RIG001..RIG020 group rig_chassis (RIG001
    # "Coffin Nail" == rig_muscle_coffin_nail, and so on down) off much thinner
    # prompts. APH has no rig_chassis key, so they fell through to props and billed
    # a SECOND time: 20 x 55 = 1,100 credits and 20 duplicate meshes, plus another
    # 55 for the duplicate pilot row. Drop them here, keep the richer bible entries.
    SKIP_GROUPS = {"rig_chassis"}
    for a in (assets["assets"] if assets else []):
        if a["group"] in SKIP_GROUPS: continue
        o, ph = APH.get(a["group"], (10, "props"))
        add(o, ph, a["assetId"], a["group"], a["prompt"], a["credits"],
            "hero" if a.get("tier") == "hero" else "standard")
    for a in (weps["assets"] if weps else []):
        o, ph = APH.get(a["group"], (10, "props"))
        add(o, ph, a["assetId"], a["group"], a["prompt"], a["credits"], "standard")

    # 0 PILOT: one of each distinct group, pulled to the front, flagged pilot
    pilot_ids, seen = [], set()
    for r in sorted(rows, key=lambda x: (x["order"], x["id"])):
        if r["group"] not in seen:
            seen.add(r["group"]); r_pilot = dict(r); r_pilot["order"] = 0
            r_pilot["phase"] = "pilot"; r_pilot["id"] = "PILOT_" + r["id"]
            pilot_ids.append(r_pilot)
    rows = pilot_ids + rows

    rows.sort(key=lambda x: (x["order"], x["id"]))
    # running credit total
    run = 0
    for r in rows:
        run += r["credits"]; r["cumulative"] = run

    payload = {"version": 1, "count": len(rows),
               "credits_total": sum(r["credits"] for r in rows),
               "rows": rows}
    out = HERE / "generation_manifest.json"
    out.write_text(json.dumps(payload, indent=2))

    ph = collections.OrderedDict()
    for r in rows:
        ph.setdefault(r["phase"], [0, 0])
        ph[r["phase"]][0] += 1; ph[r["phase"]][1] += r["credits"]
    print(f"wrote {out}\n")
    print(f"{'phase':13} {'items':>6} {'credits':>9}  {'cumulative':>11}")
    cum = 0
    for k, (n, c) in ph.items():
        cum += c
        print(f"{k:13} {n:6} {c:9,}  {cum:11,}")
    print(f"{'TOTAL':13} {len(rows):6} {payload['credits_total']:9,}  of 25,000")
    print(f"\npilot (proof before the batch commits): {len(pilot_ids)} assets, "
          f"{sum(r['credits'] for r in pilot_ids)} credits")


if __name__ == "__main__":
    main()
