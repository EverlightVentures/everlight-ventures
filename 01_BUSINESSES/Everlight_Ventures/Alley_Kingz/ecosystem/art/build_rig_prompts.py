#!/usr/bin/env python3
"""
AK-RIGART 2026-07-18 -- rig art prompts for the 20-rig bible.

Operator meshes vehicles BY HAND in Tripo Studio. What he needs from this script is not API
calls, it is (a) correctly-shaped reference-image prompts and (b) a deterministic filename so a
finished PNG drag-and-drops straight into the right slot.

Reads:  art/rig_bible.json          20 rigs (dna/look/story/personality/pride/stats/weapon/armor/synergy)
        art/build_card_roster.py    the STYLE constant, IMPORTED not copied, so the card art for
                                    rigs and the card art for dogs stay the same game.

Emits:  art/rig_prompts.json           per rig: MESH prompt + CARD prompt + filenames + mount count
        art/AK_RIG_MESH_CHECKLIST.md   top-to-bottom work order, Mythics first (the showpieces)

TWO PROMPTS PER RIG, and they are deliberately opposites:

  MESH  Tripo image-to-3D reference. One subject, plain seamless background, flat even light,
        full vehicle uncropped, 3/4 front, no motion blur, no dramatic shadow, no film grain,
        no text. This is clinical ON PURPOSE. Proven on the dog pipeline: cinematic styling
        bakes the lighting into the texture and corrupts the reconstructed geometry. Any
        drama in a MESH prompt is a bug, not a flourish.

  CARD  the cinematic hero shot for the card face. Gritty gold-cyberpunk noir, dramatic rim
        light, the STYLE block imported from build_card_roster.py.

TWO HARD GATES, both fail the build rather than emit bad art:

  1. TRADEMARK. The bible's "dna" field holds real marques and is INTERNAL ONLY. It is never
     read by this script. art/rig_bible_audit.txt found marque words leaking out of look/prompt
     (Targa, D9, Divco, Econoline, Deuce), so anything pulled off a rig runs through SCRUB
     first, and every finished prompt then runs through assert_no_marque() as the backstop for
     leaks the scrub has never heard of. Describe the silhouette, never the badge.

  2. MOUNT COUNT. Rarity sets weapon hardpoints (Common 1 ... Mythic 5). Art that shows a
     different number of guns than the stat block grants is a bug, so the count is written
     into the prompt explicitly and asserted against MOUNTS[rarity] before anything is written.
"""
import json
import re
import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
BIBLE = HERE / "rig_bible.json"
ROSTER_PY = HERE / "build_card_roster.py"


# ---------------------------------------------------------------- shared style (imported)

def load_style():
    """Import STYLE from build_card_roster.py. Never copy it -- a copy silently drifts."""
    spec = importlib.util.spec_from_file_location("_ak_card_roster", ROSTER_PY)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL: cannot load %s -- STYLE is the shared look, refusing to guess" % ROSTER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    style = getattr(mod, "STYLE", "")
    if not style or len(style) < 80:
        raise SystemExit("FAIL: STYLE missing or truncated in build_card_roster.py")
    return style


# ---------------------------------------------------------------- trademark gate

# Real marques, models and recognizable trade shorthand. Case-insensitive, word-boundary,
# hyphen/space tolerant. If any of these reaches a finished prompt the build dies.
DENYLIST = [
    "GTR", "Nissan", "Skyline", "Lamborghini", "Countach", "Porsche", "Targa", "Cadillac",
    "Rolls-Royce", "Phantom", "Mercedes", "Unimog", "Ford", "Econoline", "Divco", "Chevrolet",
    "Impala", "Silvia", "Toyota", "Hilux", "Mazda", "RX-7", "Dodge", "Charger", "Volkswagen",
    "Golf", "GTI", "Caterpillar", "Bigfoot", "Deuce",
    # beyond the required minimum, pulled from the dna fields this script must never echo
    "Benz", "GMC", "Vandura", "Miller-Meteor", "Ecto", "Land Cruiser", "Microbus", "Beetle",
    "Camaro", "Mustang", "Corvette", "Chrysler", "Plymouth", "Pontiac", "Buick", "Lincoln",
    "Bentley", "Ferrari", "Maserati", "Lotus", "Jaguar", "Aston Martin", "BMW", "Audi",
    "Subaru", "Honda", "Acura", "Lexus", "Mitsubishi", "Suzuki", "Kia", "Hyundai", "Jeep",
    "Hummer", "Peterbilt", "Kenworth", "Freightliner", "Mack Truck", "Tesla", "A-Team",
    "Batmobile", "Series 62", "F-250", "C10", "S13", "RX7",
]


def _deny_rx(term):
    """Tolerate hyphen/space/no-space variants: Rolls-Royce == Rolls Royce, RX-7 == RX 7."""
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", term) if p]
    return re.compile(r"\b" + r"[\s\-]*".join(parts) + r"\b", re.I)


DENY_RX = [(t, _deny_rx(t)) for t in DENYLIST]

# Known leak vocabulary -> silhouette wording. Sourced from art/rig_bible_audit.txt Tier 1 plus
# its soft-note list. The scrub fixes what the audit already caught; assert_no_marque() is the
# net under everything else, so a NEW leak still fails loud instead of being auto-laundered.
SCRUB = [
    (re.compile(r"\bsquare-?body\b", re.I), "square-shouldered"),
    (re.compile(r"\bfleetside\b", re.I), "straight-sided"),
    (re.compile(r"\bmicro-?bus\b", re.I), "split-window minibus"),
    (re.compile(r"\bTarga\b", re.I), "wraparound roll-hoop"),
    (re.compile(r"\bDeuce\b", re.I), "1930s"),
    (re.compile(r"\bEconoline\b", re.I), "full-size work-van"),
    (re.compile(r"\bDivco\b", re.I), "snub-nose milk-truck"),
    (re.compile(r"\bD9\b", re.I), "heavy-dozer"),
    (re.compile(r"\bBigfoot\b", re.I), "exhibition monster-truck"),
    (re.compile(r"\bUnimog\b", re.I), "portal-axle all-terrain truck"),
    (re.compile(r"\bA-Team\b", re.I), "1980s TV"),
]

SCRUB_HITS = []


def scrub(text):
    """Launder the audit's known leak vocabulary out of anything copied off a rig."""
    if not text:
        return ""
    for rx, repl in SCRUB:
        text, n = rx.subn(repl, text)
        if n:
            SCRUB_HITS.append((rx.pattern, n))
    return text


def assert_no_marque(text, where):
    """HARD GATE. A real marque in a generated prompt is a legal problem, not a style note."""
    for term, rx in DENY_RX:
        m = rx.search(text)
        if m:
            raise SystemExit(
                "FAIL trademark gate at %s -- marque '%s' found as '%s'.\n"
                "Describe the silhouette, never the badge. Fix the source field in rig_bible.json\n"
                "or add a SCRUB rule. Nothing was written." % (where, term, m.group(0))
            )


# U+2014 and U+2013 built with chr() so this source file carries no dash bytes of its own.
DASHES = {chr(0x2014): "em-dash", chr(0x2013): "en-dash"}


def assert_no_dash(text, where):
    """The workspace write guard rejects em-dash bytes. Catch them here, not at write time."""
    for ch, name in DASHES.items():
        if ch in text:
            raise SystemExit("FAIL %s at %s -- use ' -- ' instead. Nothing was written." % (name, where))


# ---------------------------------------------------------------- mounts

# Rarity grants weapon hardpoints. The art has to show exactly this many or it contradicts the
# stat block the player reads on the card.
MOUNTS = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 4, "Mythic": 5}
NUMWORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

# Auxiliary hardpoints beyond the signature weapon, per family so they stay plausible on the
# silhouette. Deterministic: a rig takes the first (count - 1) from its family pool.
AUX = {
    "muscle": [
        "a cowl-mounted stub cannon punched through the hood line",
        "a rear quarter-panel rocket tube bolted flush to the fender",
        "a trunk-lid scatter port with the deck cut open around it",
        "a rocker-panel spike rail running door to door",
    ],
    "sport": [
        "a low nose-mounted micro launcher recessed into the front valance",
        "a side-skirt flechette pod faired into the rocker",
        "a rear-deck launch tube integrated into the wing mounts",
        "a wheel-arch dart rail tucked behind the front tire",
    ],
    "van": [
        "a roof-corner turret stub on a short pedestal",
        "twin rear-door firing ports cut through the barn doors",
        "a side-panel drop hatch launcher in the sliding-door flank",
        "a flank-mounted mortar tube clamped to the belt line",
    ],
    "monster": [
        "a cab-roof pintle mount on a welded ring",
        "a bed-mounted heavy gun on the cargo deck",
        "a fender-top rocket pod over the front tire",
        "a rear-deck mortar tube braced against the frame",
    ],
}


# Mounts are listed semicolon-separated, so a signature mount carrying its own commas reads as
# extra hardpoints and blows the count the prompt just promised. Reduce it to one noun phrase:
# drop a bare positional lead ("front, a single iron spike" keeps the spike, not the word front),
# then cut at the first comma only when enough of a description already stands in front of it.
MOUNT_LEAD = re.compile(r"^(?:front|rear|roof|side|nose)s?,\s*", re.I)


def tighten_mount(text):
    text = MOUNT_LEAD.sub("", clean_clause(text))
    head = text.split(",")[0].strip()
    return head if len(head) >= 20 else text


def mount_plan(rig):
    """Signature weapon first, then family aux hardpoints, exactly MOUNTS[rarity] of them."""
    count = MOUNTS[rig["rarity"]]
    pool = AUX.get(rig["family"], AUX["muscle"])
    sig = tighten_mount(scrub((rig.get("weapon") or {}).get("mount") or "a hull-mounted gun"))
    sig = sig[0].lower() + sig[1:] if sig else sig
    mounts = [sig] + pool[: count - 1]
    if len(mounts) != count:
        raise SystemExit("FAIL mount plan for %s -- wanted %d, built %d" % (rig["id"], count, len(mounts)))
    return count, mounts


# ---------------------------------------------------------------- silhouette body

# The bible's own prompt field already carries the scrubbed silhouette, but it ships with its
# own background/lighting/negative boilerplate baked in. Strip that out so this script's much
# stricter Tripo scaffold is the only voice giving camera and lighting orders. Fragments are
# comma/period separated; a fragment dies only on a FULL match, so descriptive text survives.
BOILER = re.compile(
    r"^(?:"
    r"(?:a |the )?single (?:war-?rig )?(?:vehicle|object)(?: centered)?"
    r"|object only"
    r"|(?:single )?three-quarter(?: front)? view"
    r"|(?:plain |solid )*white background"
    r"|neutral (?:even |studio |even studio )*light(?:ing)?"
    r"|even neutral studio lighting"
    r"|clean product render"
    r"|stylized game-ready 3d asset"
    r"|blank[a-z0-9 '\-]*grille[a-z0-9 '\-]*"
    r"|(?:absolutely |and |with )?no [a-z0-9 '\-]*"
    r"(?:badge|logo|emblem|manufacturer|marque|script|text|letter|decal|watermark|character"
    r"|hand|a-pose|driver|dog|shadow|baked)[a-z0-9 '\-]*"
    r")$",
    re.I,
)

# Some source prompts open with a camera order glued to the subject by a colon rather than a
# comma, so fragment-dropping never sees it ("three-quarter view: a bastardized hot rod").
# Shave the prefix off instead of losing the subject with it.
LEAD_VIEW = re.compile(r"^(?:single vehicle[,:]\s*)?(?:single )?three-quarter(?: front)? view\s*[:,]\s*", re.I)
# "A single war-rig van" collides with the scaffold's own "a single vehicle". Drop the count word.
LEAD_SINGLE = re.compile(r"^(a |the )?single\s+(?=\S)", re.I)


def decap(frag):
    """Fragments were sentence starts; after a comma-join their capitals read as typos.

    Only lowercase a plainly capitalized ordinary word. Leave acronyms (IV-line, NIGHTSHIFT)
    and single-letter shape cues (V-creased) exactly as the bible wrote them.
    """
    head = re.match(r"[A-Za-z]+", frag)
    if not head:
        return frag
    w = head.group(0)
    if len(w) < 2 or w.isupper():
        return frag
    return frag[0].lower() + frag[1:]


def clean_clause(text):
    """Trim a clause pulled off a rig so it can be dropped mid-sentence without double punctuation."""
    return re.sub(r"\s+", " ", (text or "").strip()).strip(" .,;:")


def body_of(rig):
    """Silhouette + war mods only. Camera, light, background and negatives are ours to set."""
    src = LEAD_VIEW.sub("", scrub(rig.get("prompt") or "").strip())
    frags = [f.strip() for f in re.split(r"[.,]\s*", src) if f.strip()]
    keep = [f for f in frags if not BOILER.match(f)]
    if not keep:
        raise SystemExit("FAIL body_of stripped everything for %s" % rig["id"])
    keep = [keep[0]] + [decap(f) for f in keep[1:]]
    body = LEAD_SINGLE.sub(lambda m: (m.group(1) or "a "), ", ".join(keep))
    return body[0].upper() + body[1:]


def short_of(body, n=3):
    """First few fragments -- enough silhouette to key the card art without writing an essay."""
    return decap(", ".join(body.split(", ")[:n]))


# ---------------------------------------------------------------- the two prompts

MESH_NEG = ("cinematic lighting, dramatic lighting, rim light, god rays, lens flare, motion blur, "
            "depth of field, bokeh, film grain, vignette, colour grade, teal and orange, neon glow, "
            "reflections of a room, environment reflections, cast shadow, ground shadow, contact "
            "shadow, baked ambient occlusion, dark shadows, night, rain, wet road, smoke, dust, "
            "sparks, fire, action scene, street scene, city, garage, showroom floor, horizon line, "
            "cropped, cut off, out of frame, close-up, detail shot, wheels cropped, low angle, "
            "top-down, side profile, multiple vehicles, second car, character, driver, dog, person, "
            "hands, A-pose figure, badges, emblems, logos, manufacturer name, marque script, "
            "lettering, numbers, decals, sponsor stickers, license plate text, watermark, signature")

CARD_NEG = ("blank background, white background, product shot, flat lighting, clinical, technical "
            "drawing, orthographic, cropped vehicle, multiple vehicles, badges, emblems, logos, "
            "manufacturer name, marque script, lettering, text, watermark, signature")


def mesh_prompt(rig, body, count, mounts):
    """Clinical. Every word here exists to protect the reconstructed geometry."""
    return (
        "Clean orthographic-style reference photograph of a single vehicle for photogrammetry and "
        "image-to-3D reconstruction. "
        + body + ". "
        "Weapon hardpoints: exactly " + NUMWORD[count] + " visible weapon mounts on the body, "
        + "; ".join(mounts) + ". Each mount is clearly readable as a separate piece of hardware "
        "with visible mounting brackets, and there are no other guns on the vehicle. "
        "Bodywork is completely unbranded: blank grille, no badges, no emblems, no manufacturer "
        "name, no marque script, no lettering, no numbers, no decals, no sponsor stickers, no "
        "plate text, no writing of any kind on any panel. "
        "Framing: the complete vehicle bumper to bumper and roofline to tire contact patch, whole "
        "and uncropped, generous even margin on all four sides, nothing touching the frame edge, "
        # Never say "all four tires": the roster runs a 6x6 and a tracked dozer.
        "three-quarter front view turned about thirty degrees, camera at mid-vehicle height, level "
        "horizon, wheels straight, every wheel, tire or track fully visible and none cut off. "
        "Lighting: flat even neutral white studio light wrapping the vehicle from every side, every "
        "panel and every recess equally legible, no hotspots, no rim light, no coloured light, no "
        "light direction readable in the render. "
        "Background: plain seamless mid-grey, completely empty, no floor line, no horizon, no "
        "props, no scenery, no reflections. "
        "Render: sharp, clinical and evenly exposed edge to edge, full depth of field, no motion "
        "blur, no dramatic shadow, no cast or contact shadow under the tires, no baked ambient "
        "occlusion, no film grain, no vignette, no colour grade, no atmosphere, no character, no "
        "driver, no hands. Matte surfaces preferred over mirror chrome so the geometry reads. "
        "This is a clinical asset reference, not a hero shot."
    )


def card_prompt(rig, short, count, mounts, style):
    """The opposite job. All the drama the mesh prompt is forbidden to have."""
    effect = scrub((rig.get("weapon") or {}).get("effect") or "")
    action = clean_clause(effect.split(". ")[0]) or "erupts into the frame at full throttle"
    weapon_name = clean_clause(scrub((rig.get("weapon") or {}).get("name") or "")) or "its signature gun"
    # Personality runs from three words to a paragraph. A hero shot only needs the first beat.
    mood = clean_clause(scrub(rig["personality"]).split(". ")[0])
    return (
        "cinematic hero shot of a vehicle. Camera: dramatic low-angle hero shot on an anamorphic "
        "lens, slow motion, subtle push-in, the rig filling the frame in three-quarter front view. "
        "Subject: " + scrub(rig["name"]) + ", the " + scrub(rig["crew"]) + " " + rig["family"] +
        " war rig -- " + short + " -- carrying exactly " + NUMWORD[count] + " weapon mounts, "
        "led by " + weapon_name + " on " + clean_clause(mounts[0]) + ". "
        "Action: " + action + ", a wall of molten gold light erupting behind it, glowing embers "
        "raining down, gold catching brilliant glints along every edge, chains and plate swaying "
        "with the hit. Lighting: hard dramatic rim light carving the silhouette out of deep "
        "vanta-black, molten gold key from behind, heavy falloff into crushed shadow. "
        "Look: shot on anamorphic lens, " + style + ". "
        "Mood: " + mood + ", king of the alley, larger than life. "
        "Unbranded bodywork, blank grille, no badges, no emblems, no manufacturer name, no marque "
        "script. No text, no lettering, no watermark."
    )


# ---------------------------------------------------------------- build

RANK = {"Mythic": 0, "Legendary": 1, "Epic": 2, "Rare": 3, "Common": 4}


def build():
    style = load_style()
    bible = json.loads(BIBLE.read_text())
    rigs = bible["rigs"]

    out = []
    for rig in rigs:
        rarity = rig["rarity"]
        if rarity not in MOUNTS:
            raise SystemExit("FAIL unknown rarity %r on %s -- no hardpoint rule" % (rarity, rig["id"]))

        family = rig["family"]
        slug = rig["id"].split("_", 2)[2]
        stem = "rig_%s_%s" % (family, slug)

        body = body_of(rig)
        count, mounts = mount_plan(rig)
        mesh = mesh_prompt(rig, body, count, mounts)
        card = card_prompt(rig, short_of(body), count, mounts, style)

        # GATE 1 -- trademark, on the finished text, both prompts, plus the filenames.
        for label, text in (("MESH", mesh), ("CARD", card), ("filename", stem)):
            assert_no_marque(text, "%s %s" % (rig["id"], label))
            assert_no_dash(text, "%s %s" % (rig["id"], label))

        # GATE 2 -- mounts match the stat block, and the prompt actually says so.
        want = MOUNTS[rarity]
        if count != want or len(mounts) != want:
            raise SystemExit("FAIL mount count for %s -- %s grants %d, built %d" % (rig["id"], rarity, want, count))
        if ("exactly %s visible weapon mounts" % NUMWORD[want]) not in mesh:
            raise SystemExit("FAIL mount count not stated in MESH prompt for %s" % rig["id"])
        if ("exactly %s weapon mounts" % NUMWORD[want]) not in card:
            raise SystemExit("FAIL mount count not stated in CARD prompt for %s" % rig["id"])

        out.append({
            "id": rig["id"],
            "name": rig["name"],
            "family": family,
            "crew": rig["crew"],
            "rarity": rarity,
            "stats": rig["stats"],
            "mount_count": count,
            "mounts": mounts,
            "mesh_file": stem + "_MESH.png",
            "card_file": stem + "_CARD.png",
            "mesh_prompt": mesh,
            "mesh_negative": MESH_NEG,
            "card_prompt": card,
            "card_negative": CARD_NEG,
        })

    out.sort(key=lambda r: (RANK[r["rarity"]], r["family"], r["name"]))
    return style, out


def write_json(style, rows):
    (HERE / "rig_prompts.json").write_text(json.dumps({
        "version": 1,
        "generated_by": "art/build_rig_prompts.py",
        "source": "art/rig_bible.json",
        "note": ("dna is internal only and is never read by the generator. MESH prompts are "
                 "deliberately clinical: cinematic styling bakes into the texture and corrupts "
                 "the geometry. CARD prompts carry the shared STYLE from build_card_roster.py."),
        "style": style,
        "mount_rule": MOUNTS,
        "count": len(rows),
        "mesh_negative": MESH_NEG,
        "card_negative": CARD_NEG,
        "rigs": rows,
    }, indent=2) + "\n")


def write_checklist(rows):
    L = ["# ALLEY KINGZ -- RIG MESH CHECKLIST (20 rigs)",
         "",
         "Work top to bottom. Mythics first, they are the showpieces and they set the bar the rest",
         "get judged against. Two images per rig, then one mesh.",
         "",
         "Per rig:",
         "1. Generate the MESH image. Save it as the exact `_MESH.png` filename listed.",
         "2. Drop that PNG into Tripo Studio image-to-3D.",
         "3. Generate the CARD image. Save it as the exact `_CARD.png` filename.",
         "",
         "MESH prompts are clinical on purpose. Flat light, seamless grey, no drama. Cinematic",
         "styling bakes the lighting into the texture and corrupts the geometry, which is what went",
         "wrong on the dog pipeline. If a MESH render comes back moody, reject it and re-roll.",
         "",
         "Mount counts are set by rarity and are not cosmetic: Common 1, Rare 2, Epic 3,",
         "Legendary 4, Mythic 5. If the render shows the wrong number of guns it contradicts the",
         "card the player reads. Re-roll it.",
         "",
         "Full prompt text for every rig lives in `art/rig_prompts.json`.",
         "",
         "| # | done | rig | rarity | family | crew | mounts | mesh file | card file |",
         "|---|------|-----|--------|--------|------|--------|-----------|-----------|"]
    for i, r in enumerate(rows, 1):
        L.append("| %d | [ ] | %s | %s | %s | %s | %d | `%s` | `%s` |" % (
            i, r["name"], r["rarity"], r["family"], r["crew"], r["mount_count"],
            r["mesh_file"], r["card_file"]))

    cur = None
    for r in rows:
        if r["rarity"] != cur:
            cur = r["rarity"]
            L += ["", "---", "", "## %s" % cur.upper()]
        L += ["",
              "### %s  (%s, %s, %d mounts)" % (r["name"], r["family"], r["crew"], r["mount_count"]),
              "",
              "- MESH file: `%s`" % r["mesh_file"],
              "- CARD file: `%s`" % r["card_file"],
              "- Stats: " + ", ".join("%s %s" % (k, v) for k, v in r["stats"].items()),
              "- Mounts to show: " + "; ".join(r["mounts"]),
              "",
              "**MESH prompt**",
              "",
              "> " + r["mesh_prompt"],
              "",
              "**CARD prompt**",
              "",
              "> " + r["card_prompt"]]
    L.append("")
    (HERE / "AK_RIG_MESH_CHECKLIST.md").write_text("\n".join(L))


def main():
    style, rows = build()

    blob = json.dumps(rows)
    assert_no_dash(blob, "emitted payload")
    assert_no_marque(blob, "emitted payload")

    write_json(style, rows)
    write_checklist(rows)

    print("wrote art/rig_prompts.json + art/AK_RIG_MESH_CHECKLIST.md")
    print("rigs: %d  |  prompts: %d (%d MESH + %d CARD)" % (len(rows), len(rows) * 2, len(rows), len(rows)))
    by = {}
    for r in rows:
        by.setdefault(r["rarity"], []).append(r["mount_count"])
    print("mount gate PASS  |  " + "  ".join(
        "%s x%d = %d mount%s" % (k, len(v), v[0], "" if v[0] == 1 else "s")
        for k, v in sorted(by.items(), key=lambda kv: RANK[kv[0]])))
    print("trademark gate PASS  |  %d denylist terms checked against %d prompts + %d filenames"
          % (len(DENYLIST), len(rows) * 2, len(rows)))
    if SCRUB_HITS:
        agg = {}
        for pat, n in SCRUB_HITS:
            agg[pat] = agg.get(pat, 0) + n
        print("scrub fired: " + ", ".join("%s x%d" % (p, n) for p, n in sorted(agg.items())))
    else:
        print("scrub fired: nothing (bible source fields already clean)")
    print("style: imported from build_card_roster.py (%d chars)" % len(style))


if __name__ == "__main__":
    main()
