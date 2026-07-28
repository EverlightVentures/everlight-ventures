# AK x HIGGSFIELD -- DISTRICT MAP PROMPTS
## Staging folder for the map-art refresh (video work happens manually first)

Created: 2026-07-19 | Owner: Rich / Lucrex | Status: STAGED, NOT GENERATED YET

These are text-to-video / text-to-image prompts for regenerating the 9 district
maps and their building art. They live in their own folder ON PURPOSE: the maps
are NOT updated yet, and manual video work comes before any of these ship into
`game/assets/`. Nothing here is wired into the game.

---

## Why this folder is separate

- `AK_HIGGSFIELD_PIPELINE.md` (ecosystem root) = the CLI + credit doctrine. Read it first.
- THIS folder = the actual per-district prompt payloads, one file per district.
- `game/assets/districts/` = where finished art eventually lands. Do NOT write here
  from this folder without a visual review pass first.

## Credit discipline (from AK_HIGGSFIELD_PIPELINE.md)

- PLUS plan. Credits do NOT roll over.
- `higgsfield generate cost` BEFORE every batch. That is law.
- Use `--json` when Claude drives the CLI.
- Trailer first, then P1/P2/P3 batches.

---

## Files

| File | District | Faction city | Locked |
|---|---|---|---|
| `01_the_lot.md` | THE LOT (HOME_TURF) | Central Plaza (neutral) | no |
| `02_downtown.md` | DOWNTOWN | The Unbound | no |
| `03_neon_heights.md` | NEON HEIGHTS | The Crowned (capital) | no |
| `04_the_yards.md` | THE YARDS | The Rusted | no |
| `05_factory_row.md` | FACTORY ROW | The Rusted | no |
| `06_the_strip.md` | THE STRIP | The Unbound | no |
| `07_the_docks.md` | THE DOCKS | The Hologhosts | no |
| `08_the_overlook.md` | THE OVERLOOK | The Crowned | LOCKED |
| `09_the_undercity.md` | THE UNDERCITY | The Hologhosts | LOCKED |
| `10_master_shots.md` | full-city + faction trailer shots | -- | -- |
| `STYLE_LOCK.md` | global style prefix + negative prompts + camera vocab | -- | -- |

Each district file has: canon header, CINEMATIC prompt, ATMOSPHERIC LOOP prompt,
per-building prompts, and the exact canon facts the art must not contradict.

---

## CANON SOURCE OF TRUTH (do not drift)

Faction colors are from `game/systems/karma.js` FACTIONS, which is the ONE runtime
source (`AKKarma.getZoneFaction`) that the district banner and market tax read from:

| Faction city | Crew | Icon | Canon color | Ethos |
|---|---|---|---|---|
| The Crowned | K9 Circuitry | 👑 | `#00E0C0` teal | elite, arrogant, feared |
| The Rusted | Boneguard Crew | 🦴 | `#C9772E` rust | underground, resourceful, underestimated |
| The Hologhosts | Leashbreak Tactix | 👻 | `#7B5CFF` violet | mysterious, tech, unpredictable |
| The Unbound | Zoomie Syndicate | ⚡ | `#FF2E88` magenta | hungry underdogs, all speed |
| Central Plaza | (none) | 🏙️ | `#e8c55a` gold | neutral ground |

The crew-badge colors in `AK_BLOCK_CHRONICLES_BIBLE.md` §1.1 are the SECONDARY
badge palette (gold / green / violet / blue). The karma.js colors above are the
DISTRICT ENVIRONMENT colors. When a prompt describes district lighting, use the
karma.js color. When it describes a dog's colors/armor, use the badge color.

## KNOWN CANON CONFLICT (flagged, not resolved)

`AK_BLOCK_CHRONICLES_BIBLE.md` §1.1 puts **K9 Circuitry on THE DOCKS**.
`karma.js` + `AK_CITY_DEPTH_PLAN.md` put **Leashbreak / Hologhosts on THE DOCKS**.

These prompts follow **karma.js**, because that is what the running game renders.
This is the two-faction-taxonomy conflict already logged in the 2026-07-17 audit.
Resolve it in the Bible before these maps ship, or the art will contradict the text.

## FORBIDDEN (from Bible §7)

- `North//Block` is not a district. The northern locked district is **THE OVERLOOK**.
- `Handler//compound` is not a place. Handlers live at **THE KENNEL** in **THE LOT**.
- "crew" never "clan."
