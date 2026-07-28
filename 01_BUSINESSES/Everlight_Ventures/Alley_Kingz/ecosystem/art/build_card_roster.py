#!/usr/bin/env python3
"""
Alley Kingz -- the 106-card master roster + the ROOT TEMPLATE every card follows.

Operator 2026-07-17: wants ONE list of all 106 cards (name, story, description, tagline) that
all follow a single root theme template, so the Higgsfield full-body art is CONSISTENT. The
template is the generalized $BCARDD canon lock (AK_DESIGN_BIBLE line 99: "wardrobe/accessories
vary, the dog does not") + the upright-bipedal walk-clip rule (line 77).

Reads the canon we already wrote (never re-invent):
  cards.json         name, breed, faction, rarity, class, rig
  cards_lore.js      tagline + bio (description), 106/106
  cards_stories.js   themes (the story essence), 106/106
  rig_bible.json     the 20 authored war rigs the cards are assigned to

Emits:
  AK_106_CARD_ROSTER.md   human-readable list, grouped by rarity
  card_roster.json        data + the per-dog Higgsfield full-body prompt

AK-RIGMERGE 2026-07-18: every card now carries a REAL rig out of rig_bible.json (shared across
dogs, like real makes) instead of a "{Breed} Rig" placeholder. This builder carries that through
to the roster AND guards it -- check_rig_merge() hard-fails the build if a future regeneration of
cards.json reintroduces placeholder rigs, empty flavor, or orphaned bible rigs. The rig is DATA
here, deliberately not injected into the portrait prompt: NEG already bans "riding a vehicle",
so these stay clean full-body dog cutouts. Rig art lives in build_rig_prompts.py.

The per-dog prompt = ROOT TEMPLATE + this dog's breed + faction look + rarity gear. Consistency
comes from the template; distinctness comes from breed + faction + their signature. NO card art
is used as a reference (that dragged output into framed illustrated card scenes -- off-model).
"""
import json, re, collections
from pathlib import Path

HERE = Path(__file__).parent
GAME = HERE.parent / "game"

# THE ROOT TEMPLATE. Every card is this shape; only the bracketed parts change.
# THE ALLEY KINGZ MASTER STYLE (from Rich's win.mp4 master prompt, 2026-07-18). This exact style
# block is the theme. Only breed + gear change per dog. Do NOT reintroduce the word
# "hyper-realistic" or "photorealistic human bodybuilder" -- the STYLE keywords below are what make
# it cinematic-cool instead of clinical-ugly.
STYLE = ("dark gritty 1990s neo-noir comic aesthetic, twisted metal energy, gold cyberpunk palette, "
         "molten gold on deep vanta-black shadow, dramatic volumetric lighting, deep crushed shadows, "
         "heavy atmosphere, film grain, ultra detailed textures, cinematic film-still quality, "
         "king-of-the-alley energy, larger than life")

# MESH variant: same theme, but full-body A-pose on a clean cutout so Tripo can turn it 3D.
ROOT = ("full body cinematic 3D character render of an upright BIPEDAL anthropomorphic {breed} "
        "gangster dog in the signature Alley Kingz style. {breed} with a real expressive dog head "
        "and a powerful heroic build, confident menacing king-of-the-alley swagger. {faction_look}. "
        "{rarity_gear}, all gear rendered rich glamorous molten gold. Standing in a relaxed "
        "confident heroic A-pose, arms slightly away from the torso, front facing, the ENTIRE body "
        "from head to the soles of BOTH feet, both feet flat and fully visible with a margin below, "
        "a dog tail clearly visible. Look: " + STYLE + ". Simple dark studio background, the whole "
        "character fully and evenly lit and visible for a clean cutout, no scenery, no brand logos, "
        "no swoosh, no lettering, no text, no watermark.")

# CARD-ART variant: Rich's master hero shot, verbatim structure, for the card portrait / cinematics.
CARD_ART = ("cinematic hero shot. Camera: dramatic low-angle hero shot on an anamorphic lens, slow "
            "motion, subtle push-in. Subject: a muscular upright anthropomorphic {breed} gangster "
            "dog king, {faction_look}, {rarity_gear}. Action: a wall of molten gold light erupts "
            "behind him in slow motion, glowing embers raining down, gold catching brilliant glints, "
            "chain swaying, triumphant champion energy. Look: shot on anamorphic lens, " + STYLE +
            ". Mood: victorious, king of the alley, larger than life. No text, no watermark.")

NEG = ("four legged, quadruped, on all fours, bust, portrait crop, cropped legs, cut off at "
       "waist, no feet, no tail, arms crossed, arms at sides, walking, mid-stride, action pose, "
       "framed card border, background scenery, city, neon, riding a vehicle, text, watermark, "
       "brand logo, nike swoosh, branded sneakers, adidas, jordan, lettering on clothing, "
       "garbled text, belt text, words on the belt, speedo, briefs, thong, loincloth, underwear, "
       "gladiator briefs, armored briefs, bare legs, naked lower body, no pants")

# old faction name -> the look block (the 8-crew rename lives in the rig map; here we key by the
# faction as stored on the card so nothing breaks)
FACTION_LOOK = {
    "Boneguard Crew":   "heavy enforcer styling, bone and gold accents, plated street armor",
    "Zoomie Syndicate": "lean chrome-and-neon streetwear, speed-runner styling",
    "Leashbreak Tactix":"tactical utility straps and a broken-chain motif",
    "K9 Circuitry":     "cyber-tech styling with subtle glowing circuitry and chrome",
}
RARITY_GEAR = {
    "Mythic":    "wearing a gold crown, flag-tint aviator sunglasses, a cigar, a thick gold cuban "
                 "chain with a medallion, an open vest, blue jeans, and heavy boots, full king loadout",
    "Legendary": "wearing flag-tint aviator sunglasses, a gold chain, an open vest, blue jeans, and "
                 "heavy boots",
    "Epic":      "wearing aviator sunglasses, a gold chain, a street jacket, blue jeans, and boots",
    "Rare":      "wearing a gold chain, a hoodie, blue jeans, and sneakers",
    "Common":    "wearing a plain tank top, blue jeans, and work boots",
}


# AK-RIGMERGE 2026-07-18: engine.js:70 RIG_GLYPH keys on rig.sourceCar and falls back SILENTLY to
# 'M', so a broken lookup mis-renders as a Muscle Car instead of erroring. Assert DIRECT hits.
RIG_GLYPH = {"Muscle Car": "M", "Sport": "S", "Van": "V", "Monster Truck": "T"}
FAMILY_SOURCE_CAR = {"muscle": "Muscle Car", "sport": "Sport", "van": "Van", "monster": "Monster Truck"}
BESPOKE_RIGS = {"The Crown Rig"}          # $BCARDD only, authored outside the bible


def check_rig_merge(dogs):
    """Hard-fail if a regeneration undid the rig merge. Cheap insurance, run every build."""
    bible = json.loads((HERE / "rig_bible.json").read_text())["rigs"]
    by_id = {r["id"]: r for r in bible}
    bad = []
    for d in sorted(dogs.values(), key=lambda d: d["num"]):
        rig, who = d["rig"], "%s %s" % (d["num"], d["name"])
        if not rig.get("name"):
            bad.append(who + ": no rig"); continue
        if rig["name"] not in BESPOKE_RIGS:
            if rig["name"] == (d["breed"] or "") + " Rig" or rig["name"] == d["name"] + " Rig":
                bad.append(who + ": placeholder rig %r is back" % rig["name"]); continue
            if rig.get("rigId") not in by_id:
                bad.append(who + ": rigId %r is not in rig_bible.json" % rig.get("rigId")); continue
            fam = by_id[rig["rigId"]]["family"]
            if rig.get("rigFamily") != fam:
                bad.append(who + ": rigFamily %r != bible %r" % (rig.get("rigFamily"), fam))
            if rig.get("sourceCar") != FAMILY_SOURCE_CAR[fam]:
                bad.append(who + ": sourceCar %r wrong for family %s" % (rig.get("sourceCar"), fam))
        if rig.get("sourceCar") not in RIG_GLYPH:
            bad.append(who + ": sourceCar %r is not a direct RIG_GLYPH hit" % rig.get("sourceCar"))
        if not (rig.get("flavor") or "").strip():
            bad.append(who + ": empty flavor")
    used = {d["rig"].get("rigId") for d in dogs.values()}
    for orphan in sorted(r["name"] for r in bible if r["id"] not in used):
        bad.append("orphaned bible rig: " + orphan)
    if bad:
        raise SystemExit("FAIL: the rig merge was undone.\n  " + "\n  ".join(bad))
    print("rig merge OK: %d cards, %d bible rigs used, 0 orphans, 0 empty flavor, %d/%d direct glyph hits"
          % (len(dogs), len(bible), len(dogs), len(dogs)))


def load():
    cards = {str(c["cardNumber"]).zfill(4): c for c in json.loads((HERE.parent / "unity_migration" / "cards.json").read_text())["cards"]}
    lore = (GAME / "cards_lore.js").read_text()
    stories = (GAME / "data" / "cards_stories.js").read_text()
    def lget(cid, f):
        m = re.search(r'"' + cid + r'"\s*:\s*\{[^}]*?' + f + r':\s*"((?:[^"\\]|\\.)*)"', lore, re.S)
        return m.group(1).replace('\\"', '"') if m else ""
    def themes(cid):
        # anchor on the ENTRY start ("NNNN": {) not any cross-reference to this cardNumber
        m0 = re.search(r'"' + cid + r'"\s*:\s*\{', stories)
        if not m0: return []
        m = re.search(r'themes:\s*\[([^\]]*)\]', stories[m0.start():m0.start() + 3000])
        return re.findall(r'"([^"]+)"', m.group(1)) if m else []
    out = {}
    for cid, c in cards.items():
        out[cid] = {
            "num": cid, "name": c.get("name"), "breed": c.get("breed"),
            "faction": c.get("class"), "rarity": c.get("rarity"),
            "role": (c.get("rig") or {}).get("rigClass"),
            "rig": c.get("rig") or {},          # AK-RIGMERGE: the assigned rig travels with the dog
            "tagline": lget(cid, "tagline"), "description": lget(cid, "bio"),
            "themes": themes(cid),
        }
    return out


def prompt_for(d, template):
    return template.format(
        breed=d["breed"] or "pitbull",
        faction_look=FACTION_LOOK.get(d["faction"], "gritty street-gang styling"),
        rarity_gear=RARITY_GEAR.get(d["rarity"], RARITY_GEAR["Common"]),
    )


def main():
    dogs = load()
    check_rig_merge(dogs)                                  # AK-RIGMERGE guard, before anything ships
    for d in dogs.values():
        d["higgsfield_prompt"] = prompt_for(d, ROOT)       # MESH reference (the batch uses this)
        d["card_art_prompt"] = prompt_for(d, CARD_ART)     # cinematic card portrait
        d["negative"] = NEG

    # json
    ordered = sorted(dogs.values(), key=lambda d: d["num"])
    (HERE / "card_roster.json").write_text(json.dumps(
        {"version": 1, "root_template": ROOT, "negative": NEG, "count": len(ordered),
         "cards": ordered}, indent=2))

    # markdown, grouped by rarity (Mythic first)
    RANK = {"Mythic": 0, "Legendary": 1, "Epic": 2, "Rare": 3, "Common": 4}
    L = ["# ALLEY KINGZ -- THE 106-CARD ROSTER\n",
         "## THE ROOT TEMPLATE (every card follows this, only the [breed]/[faction]/[gear] change)\n",
         "> " + ROOT.replace("{breed}", "[BREED]").replace("{faction_look}", "[FACTION LOOK]").replace("{rarity_gear}", "[RARITY GEAR]") + "\n",
         "The template is the law. Consistency = the template. Distinctness = breed + faction + rarity gear + the dog's own signature. Wardrobe varies, the upright-gangster-dog form never does.\n",
         "Pipeline: this description -> Higgsfield full-body portrait -> you mesh in Tripo Studio -> 3D.\n"]
    by = collections.Counter(d["rarity"] for d in dogs.values())
    L.append("Roster: " + ", ".join(f"{r} {by[r]}" for r in RANK) + f"  (total {len(dogs)})\n")
    for rarity in sorted(RANK, key=lambda r: RANK[r]):
        grp = sorted([d for d in dogs.values() if d["rarity"] == rarity], key=lambda d: d["num"])
        if not grp: continue
        L.append(f"\n---\n\n## {rarity.upper()}  ({len(grp)})\n")
        for d in grp:
            L.append(f"**{d['num']} -- {d['name']}**  ({d['breed']}, {d['faction']}, {d['role']})")
            L.append(f"- *Tagline:* {d['tagline']}")
            L.append(f"- *Description:* {d['description']}")
            if d["rig"].get("name"):        # AK-RIGMERGE: which of the 20 war rigs this dog drives
                L.append(f"- *Rig:* {d['rig']['name']} ({d['rig'].get('rigFamily', '?')}) -- {d['rig'].get('flavor', '')}")
            if d["themes"]:
                L.append(f"- *Themes:* {', '.join(d['themes'])}")
            L.append("")
    (HERE / "AK_106_CARD_ROSTER.md").write_text("\n".join(L))

    print("wrote AK_106_CARD_ROSTER.md + card_roster.json")
    print(f"cards: {len(dogs)}  |  by rarity: {dict(by)}")
    print("\nsample prompt (0001 $BCARDD):")
    print(" ", dogs["0001"]["higgsfield_prompt"][:240], "...")


if __name__ == "__main__":
    main()
