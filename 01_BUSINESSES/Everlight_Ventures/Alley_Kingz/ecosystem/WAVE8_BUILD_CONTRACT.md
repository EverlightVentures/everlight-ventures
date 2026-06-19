# WAVE 8 BUILD CONTRACT (operator "yes all the above", 2026-06-13)
Source design docs: TAXONOMY_DESIGN.md (specializations, loot tags), LOOT_SYSTEM_DESIGN.md,
BALANCE_AUDIT_REPORT.md (spell/air/faction flags), ARENA_CAMERA_TILT_BRIEF_PHASE2.md (B2).

## TRACK A -- BUILDABLE NOW (one implementation workflow, serialized, QA-gated, e5 ship)
A1. LOOT PHASE 2 (// AK-LOOT2): extend AK-LOOT with KEY-TAG drops (chest keys as rare battlefield
    loot) + CARD-COPY SHARDS (collect N shards -> a copy of a themed card); drop tables by unit
    rarity/cost per LOOT_SYSTEM_DESIGN; banks through the district gate like phase-1 loot;
    miniaturized real-art tokens; per-match budget guard.
A2. SPECIALIZATIONS (// AK-SPEC): DA:I-style -- at player level 10 choose 1 of 3 specialization
    paths per branch (Muscle/Hustle/Tech), each unlocking exclusive high-tier skill nodes; respec
    at a premium; identity-defining per the skill-tree research law. Persist ak_profile.spec.
A3. MAP BACKDROPS (// AK-MAPBG): use the painted assets/maps/<city>/L<NN>_<district>.png as the
    in-match BACKDROP per city/level/section (currently only level tiles use them); graceful
    fallback to legacy arena art when a map is not painted yet (onerror); LOW_FX safe.
A4. SPELL-DAMAGE REBALANCE (// AK-SPELLFIX, canon.js spells ONLY): the audit found damage spells
    kill nothing (Strike 320 vs min troop HP 504, Jolt 130 = chip). Raise damage-spell impact so
    they kill the cheapest real troops (Strike -> ~520, scale others proportionally) WITHOUT making
    them oppressive; keep CC spells (Freeze/Tar/Snare) as priced. QA diff = spells only.
A5. AIR-DOMAIN STREET-MELEE FIX (// AK-AIRFIX, canon.js): the audit flagged Street melee
    skirmishers (Nitro/Spike etc) as AIR-domain at melee range -- 35 ground cards can never hit
    them. Per audit: move Street melee skirmishers to GROUND domain (or give more anti-air). Apply
    the domain correction to the flagged cards; QA diff = only those cards' domain field.
A6. FACTION-PARITY TUNE (// AK-FACTION, canon.js): the audit found a 33% raw power/energy gap
    (Zoomie 93.7 high, K9 70.5 low). Small corrective nudge toward parity on the most-off outliers
    per faction (do NOT touch cards already tuned in the balance pass); conservative, within budget.
A7. CAMERA TILT B2 (// AK-TILT2): the upright/billboarded-sprite version per
    ARENA_CAMERA_TILT_BRIEF_PHASE2.md -- ISOLATED lane, highest regression risk (changes the draw
    transform). Units stand upright on the tilted ground plane; ground tilts, characters do not.
    MUST keep canvasToArena tap-accuracy exact (deploy where you tap, esp. top 20%); kill-switch
    TILT2_ENABLED=false reverts to the shipped B1. If tap accuracy cannot be guaranteed, SHIP B1
    (do not regress placement) and report B2 as needs-more-work.

## TRACK B -- DESIGN FIRST (design-only workflow, NO code, NO credit spend)
B1. REAL-TIME PvP + CLANS architecture: realtime authoritative server options (the game is static
    CF Pages today -- needs a server: Supabase Realtime? a small authoritative match server on e5/
    Railway?), matchmaking, anti-cheat (server-authoritative match resolution), presence, clans +
    clan wars data model, cost per option, and a PHASED plan (phase 1 = async "ghost" PvP vs a
    snapshot of another player's deck/AI, cheapest path to a PvP feel before true realtime).
    Output: PVP_CLANS_ARCHITECTURE.md + a recommendation + the one operator decision.
B2. ELEVENLABS PREMIUM VOICES plan: cost estimate for 111 lines (chars x ElevenLabs rate),
    hosting plan (where 111 mp3s live + deploy size impact), the wiring (preload/stream, fallback
    to the free speechSynthesis when an mp3 is missing), and a 3-CARD QUALITY SAMPLE spec so Rich
    hears it before spending on all 111. Output: ELEVENLABS_VOICE_PLAN.md. Do NOT call the API yet.

## RULES (Track A): no em-dash (use --), headless guards, protected constants
## (MATCH_TIME 180, [45,90,135] timeout path, baseR 0.78, canvas 540x900, TILT_ENABLED B1 stays
## unless B2 cleanly supersedes), all prior markers intact, harness clean, e5 ship.sh deploy.
