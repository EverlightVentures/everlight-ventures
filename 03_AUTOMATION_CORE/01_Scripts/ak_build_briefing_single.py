#!/usr/bin/env python3
"""
Alley Kingz -- build the ONE-FILE briefing.

Operator 2026-07-18: "I can only upload one file so aggregate all that into one file and then
separate it, so my bot can read it and it makes sense."

So: one Markdown file, hard section delimiters, a table of contents, and every section labelled with
what it is and where it came from. Designed to be pasted/uploaded to another AI agent.

SIZE DISCIPLINE (why this is not a raw concatenation):
The raw packet is 3.2 MB, which is roughly 800k tokens and will not fit in most agents' context.
The bulk is production noise, not meaning:
  - cards_stories.js is 1.36 MB and is mostly `panelPrompts` (image-generation prompts for the comic).
    We keep every card's NARRATIVE fields and drop the art prompts.
  - the big code files are 100-140 KB each of implementation. We keep the architecture: header
    comments, exported API surface, and function signatures.
Everything that carries MEANING about the game is kept in full: all design docs, all 106 cards with
full stats and lore, crews, rigs, bosses.
"""
import json, re, html, sys
from pathlib import Path

PACK = Path("/tmp/claude-0/-mnt-sdcard-AA-MY-DRIVE/8bef3d05-8e5c-4f39-8b88-927c8f593cf4/scratchpad/pack/ALLEY_KINGZ_BRIEFING")
OUT = Path("/mnt/sdcard/AA_MY_DRIVE/07_STAGING/Inbox/ALLEY_KINGZ_COMPLETE_BRIEFING.md")

BAR = "=" * 78


def sec(n, title, note=""):
    s = f"\n\n{BAR}\n===== SECTION {n}: {title}\n"
    if note:
        s += f"----- {note}\n"
    return s + BAR + "\n"


def detag(t):
    """HTML doc -> readable text."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|h\d|li)>", "\n", t, flags=re.I)
    t = re.sub(r"</t[dh]>", " | ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def jsblock(path, key_re):
    """Pull `"NNNN": { ... }` entries out of a .js data file."""
    src = (PACK / path).read_text(errors="ignore")
    out = {}
    for m in re.finditer(r'"(\d{4})"\s*:\s*\{', src):
        cid, start = m.group(1), m.end()
        depth, i = 1, start
        while depth and i < len(src):
            if src[i] == "{": depth += 1
            elif src[i] == "}": depth -= 1
            i += 1
        out[cid] = src[start:i]
    return out


def field(blob, name):
    m = re.search(r'\b' + name + r'\s*:\s*"((?:[^"\\]|\\.)*)"', blob, re.S)
    return m.group(1).replace('\\"', '"').replace("\\n", " ").strip() if m else ""


def main():
    L = []
    L.append("# ALLEY KINGZ -- COMPLETE BRIEFING (single file)\n")
    L.append("Generated 2026-07-18 by the Alley Kingz build system. Live game: https://alleykingz.online\n")
    L.append("""
## HOW TO READ THIS FILE

This is an aggregation of 39 source files into one document so it can be uploaded in a single
upload. Every section is delimited by a line beginning with `===== SECTION N:` and labelled with its
original filename, so you can treat each as its own document.

WHAT WAS KEPT IN FULL: every design doc, every one of the 106 cards with full stats, ability, crew,
faction, rarity, tagline, bio and story, the 8 crews, the 20 war rigs, the 12 bosses.

WHAT WAS CONDENSED, AND WHY: the raw packet is 3.2 MB (~800k tokens) which exceeds most context
windows. Two things were reduced, neither of which carries meaning about the game:
  1. `panelPrompts` -- image-generation prompts for the comic panels (1.36 MB, ~40% of the bulk).
     Every card's narrative content is kept; only the art prompts are dropped.
  2. Implementation bodies of the six large code files. Their architecture is kept: header comments,
     exported API and function signatures.
If you need the raw files, ask the operator for ALLEY_KINGZ_BRIEFING_2026-07-18.zip.

READER WARNING -- three architecture facts that fresh readers reliably get wrong:
  1. The hub camera CENTERS on the player (`cam.x = me.x - W/2`). The hero holding the middle of the
     screen while the world scrolls is CORRECT, not a stuck-movement bug.
  2. Districts are a deliberate 3x3 grid of discrete scenes with opposite-edge spawns (the Stardew
     rule), and the black-screen + gold particle wall between them is an AUTHORED transition, not a
     loading artifact or a bug.
  3. There are TWO builds: `index.html` is the walkable hub, `game.html` is the battler. A system
     missing from one is often live in the other.
""")

    toc = []
    body = []
    n = 0

    # ---- 1. the briefing ----------------------------------------------------
    n += 1
    toc.append(f"{n}. THE BRIEFING (start here) -- docs/AK_BRIEFING.md")
    body.append(sec(n, "THE BRIEFING (START HERE)", "source: docs/AK_BRIEFING.md"))
    body.append((PACK / "docs/AK_BRIEFING.md").read_text(errors="ignore"))

    # ---- 2. design docs -----------------------------------------------------
    docs = sorted(p for p in (PACK / "docs").iterdir() if p.name != "AK_BRIEFING.md")
    n += 1
    toc.append(f"{n}. DESIGN DOCS ({len(docs)} documents, full text)")
    body.append(sec(n, f"DESIGN DOCS ({len(docs)} documents)", "each doc delimited by --- DOC: <filename> ---"))
    for p in docs:
        t = p.read_text(errors="ignore")
        if p.suffix.lower() in (".html", ".htm"):
            t = detag(t)
        body.append(f"\n\n--- DOC: {p.name} ---\n\n{t}\n")

    # ---- 3. the 106-card roster --------------------------------------------
    cards = json.loads((PACK / "data/cards.json").read_text())["cards"]
    bonds = json.loads((PACK / "data/pack_bonds.json").read_text())["dogs"]
    lore = jsblock("data/cards_lore.js", None)
    stories = jsblock("data/cards_stories.js", None)

    n += 1
    toc.append(f"{n}. THE {len(cards)}-CARD ROSTER (complete: stats, crew, faction, lore, story)")
    body.append(sec(n, f"THE {len(cards)}-CARD ROSTER", "sources: cards.json + cards_lore.js + cards_stories.js + pack_bonds.json"))
    body.append("""
TWO-AXIS MODEL (important, and new as of 2026-07-18):
  CREW    = where the dog is FROM (origin block). 8 crews. This is the faction identity.
  FACTION/CLASS = what he FIELDS (the deck axis). 4 classes, 11-card decks keyed off this.
These are deliberately separate axes. No token is shared between them. The crew formerly called
BONEGUARD was renamed CROWN LOT to remove a collision with the 'Boneguard Crew' class.
""")
    crews = {}
    for c in cards:
        crews.setdefault((bonds.get(str(c["cardNumber"]).zfill(4), {}) or {}).get("originCrew", "?"), []).append(c["name"])
    body.append("\nCREW COUNTS: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(crews.items(), key=lambda x: -len(x[1]))) + "\n")

    for c in sorted(cards, key=lambda x: str(x["cardNumber"])):
        cid = str(c["cardNumber"]).zfill(4)
        b = bonds.get(cid, {}) or {}
        lo = lore.get(cid, "")
        st = stories.get(cid, "")
        ab = c.get("ability") or {}
        body.append(f"""
[{cid}] {c.get('name')}
  breed: {c.get('breed')} | rarity: {c.get('rarity')} | role: {c.get('role')} | cost: {c.get('cost')}
  crew (origin): {b.get('originCrew','?')} | class (deck axis): {c.get('class')}
  stats: hp {c.get('hp')} dmg {c.get('damage')} atk_spd {c.get('attack_speed')} move {c.get('move_speed')} range {c.get('range')}
  ability: {ab.get('name','')} -- {ab.get('description','')} (cd {ab.get('cooldown','')})
  rig: {c.get('rig')} | domain: {c.get('domain')}
  tagline: {field(lo,'tagline')}
  bio: {field(lo,'bio')}
  codename: {field(st,'codename')}
  public hook: {field(st,'publicHook')}
  core wound: {field(st,'coreWound')}
  defining choice: {field(st,'definingChoice')}
  secret truth: {field(st,'secretTruth')}
  allies: {','.join(b.get('allies',[]) or []) or '-'} | rivals: {','.join(b.get('rivals',[]) or []) or '-'}
""")

    # ---- 4. bosses ----------------------------------------------------------
    n += 1
    toc.append(f"{n}. BOSSES (12) -- data/bosses_stories.js")
    body.append(sec(n, "BOSSES", "source: data/bosses_stories.js (narrative fields; panelPrompts dropped)"))
    # bosses live in a BOSSES object keyed by BARE identifiers (LOT_WARDEN: { ... }), not "NNNN"
    bsrc = (PACK / "data/bosses_stories.js").read_text(errors="ignore")
    bstart = bsrc.find("var BOSSES")
    nb = 0
    for m in re.finditer(r'^\s{2,6}([A-Z][A-Z0-9_]+)\s*:\s*\{', bsrc[bstart:], re.M):
        k, s0 = m.group(1), bstart + m.end()
        depth, i = 1, s0
        while depth and i < len(bsrc):
            if bsrc[i] == "{": depth += 1
            elif bsrc[i] == "}": depth -= 1
            i += 1
        blob = bsrc[s0:i]
        if not field(blob, "codename"):
            continue
        nb += 1
        meta = re.search(r"act:\s*(\d+).*?breed:\s*\"([^\"]*)\".*?clanTurf:\s*\"([^\"]*)\"", blob, re.S)
        body.append(
            f"\n[{k}] {field(blob,'codename')}\n"
            f"  title: {field(blob,'title')}\n"
            f"  faction: {field(blob,'faction')} | turf: {field(blob,'turf')}\n"
            + (f"  act {meta.group(1)} | breed: {meta.group(2)} | clan turf: {meta.group(3)}\n" if meta else "")
            + f"  hook: {field(blob,'publicHook')}\n"
              f"  wound: {field(blob,'coreWound')}\n"
            # NB: bosses carry no definingChoice/secretTruth (those are dog-book fields only).
            # Their equivalent colour is themes + overlord, so emit that instead of empty lines.
            + (lambda th, ov: (f"  themes: {th}\n" if th else "") + (f"  overlord: {ov}\n" if ov else ""))(
                ", ".join(re.findall(r'"([^"]+)"', (re.search(r'themes:\s*\[([^\]]*)\]', blob, re.S) or type("x", (), {"group": lambda s, n: ""})()).group(1))),
                field(blob, "overlord")))
    body.append(f"\n(bosses emitted: {nb})\n")

    # ---- 5. rigs ------------------------------------------------------------
    n += 1
    toc.append(f"{n}. WAR RIGS (20) -- art/rig_bible.json")
    body.append(sec(n, "WAR RIGS", "source: art/rig_bible.json"))
    rigs = json.loads((PACK / "data/rig_bible.json").read_text())
    for r in rigs.get("rigs", []):
        body.append(f"\n[{r.get('id')}] {r.get('name')} | crew: {r.get('crew')} | class: {r.get('rigClass')}\n"
                    f"  {r.get('story') or r.get('description') or ''}\n"
                    f"  stats: {json.dumps({k:v for k,v in r.items() if isinstance(v,(int,float))})}\n")

    # ---- 6. code architecture ----------------------------------------------
    n += 1
    code = sorted((PACK / "code_samples").iterdir())
    toc.append(f"{n}. CODE ARCHITECTURE ({len(code)} systems: API surface + signatures)")
    body.append(sec(n, "CODE ARCHITECTURE", "header comments + exported API + function signatures; bodies omitted"))
    for p in code:
        src = p.read_text(errors="ignore")
        head = "\n".join(src.split("\n")[:40])
        sigs = re.findall(r"^\s*(?:function\s+\w+\s*\([^)]*\)|(?:var|const|let)\s+\w+\s*=\s*function\s*\([^)]*\)|\w+\s*:\s*function\s*\([^)]*\))", src, re.M)
        if p.name == "hub3d.js":                       # small + directly relevant: keep whole
            body.append(f"\n\n--- SYSTEM: {p.name} (FULL SOURCE) ---\n\n```js\n{src}\n```\n")
        else:
            body.append(f"\n\n--- SYSTEM: {p.name} ({len(src)//1024} KB) ---\n\nHEADER:\n```js\n{head}\n```\n\n"
                        f"API SURFACE ({len(sigs)} functions):\n```js\n" + "\n".join(s.strip() for s in sigs) + "\n```\n")

    OUT.write_text("\n".join(L) + "\n## TABLE OF CONTENTS\n\n" + "\n".join(toc) + "\n" + "\n".join(body))
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT}")
    print(f"size: {kb:.0f} KB  (~{int(OUT.stat().st_size/4/1000)}k tokens)")
    print(f"sections: {n} | cards: {len(cards)} | docs: {len(docs)} | code systems: {len(code)}")


if __name__ == "__main__":
    main()
