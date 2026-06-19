# ALLEY KINGZ -- SEEDANCE / SEEDREAM ART PROMPT SHEET (copy-paste)
**Run these in the Seedance UI (logged in as 1m.rich.gee@gmail.com). One pass, no back-and-forth.**
Seedream = stills (icons/cards/maps). Seedance = video (hero loops, optional). Date: 2026-06-15

## HOUSE STYLE (prepend to EVERY prompt)
`Gritty cyberpunk dog-gang trading-card art, TV-MA, neon-on-wet-concrete, gold rim light, deep black
#0A0A0A background, cinematic, high detail, sharp, no text, no watermark, no humans --` then the subject.

Faction accent colors: Boneguard = bone-white + blood-gold | Zoomie Syndicate = cyan/magenta neon |
Leashbreak Tactix = amber/rust | K9 Circuitry = electric teal/green.

## 1. MENU / LOBBY  (the premium front door)
| File | Aspect | Prompt (after the house style) |
|---|---|---|
| `assets/ui/lobby_hero.png` (the VIDEO POSTER -- shows while menu_bg.mp4 buffers; optional now) | **9:16 portrait 1080x1920** | a regal alpha dog "alley king" on a wrecked-car throne in a neon alley at night, gold crown of light, rain, full-body vertical, dramatic low angle |
| ~~`play_bg.png`~~ -- NOT NEEDED. The menu_bg.mp4 video wallpaper already covers the full screen behind PLAY. Skip it. | -- | -- |
| tab icon: Drip | 1:1 512 | a chrome spray-can crossed with a gold crowned dog-tag, neon outline icon |
| tab icon: Crew | 1:1 512 | a riot shield stamped with a glowing dog-paw sigil, chain-link texture, icon |
| tab icon: Pass | 1:1 512 | a gold medal shaped like a dog bone on a season ribbon, icon |
| tab icon: Hit List | 1:1 512 | a red crosshair over a clipboard hit-list, gritty icon |
| Faction crest x4 | 1:1 512 each | emblem: Boneguard skull-and-bone / Zoomie speed-bolt / Leashbreak broken-chain / K9 circuit-paw, each in its faction color, embossed metal |

## 2. HANDLER PORTRAITS  (the 6 dog "operators" -- HANDLER_CLASSES_SPEC.md)
3:4 portrait 768x1024 each, after the house style:
- **The Mender** -- a calm St. Bernard field-medic, gold cross on a battle-vest, healing-green glow, Boneguard white
- **The Tracker** -- a lean Bloodhound scout, glowing scent-probe drone, teal K9-Circuitry tech, alert
- **The Shadow** -- a sleek black Basenji ninja, cyan smoke trail, mid-dash, Zoomie neon
- **The Rigger** -- a Doberman engineer in a tool-harness deploying a turret, electric-teal sparks
- **The Bruiser** -- a massive scarred Pit/Mastiff tank, amber war-paint, roaring, Leashbreak rust
- **The Dealer** ($BCARDD) -- a silver Afghan-hound dealer in a velvet collar flipping a glowing gold $BCARDD card, casino-gold, mysterious (the coin's avatar; card #0001 vibe)

## 3. CARDS  (the unpainted roster)
Run per the card manifest (`ecosystem/data/cards.json`) -- any card whose `assets/cards/<slug>.png` is missing.
3:4 portrait 768x1024, after the house style: `a [breed] [role] piloting a [rig], [faction] colors, action pose`.
(The art-factory queue already lists these; the same prompts feed Seedream instead of the dead Leonardo.)

## 4. MAPS  (the unpainted cities -- STORYLINE_CANON.md)
16:9 wide 1600x900 each, after the house style, top-down-ish battle-arena backdrop, no units:
- **undercity_subway** -- flickering tube-light subway platform, grimy tile, jammed signals
- **skyline_rooftops** -- pink-gold dawn over helipads + antenna forests, the city below
- **toxic_sewers** -- sickly-green dripping pipes, biohazard glow, "the poison works"
- **casino_strip** -- gold marquee + slot glow, a boulevard that never sleeps, a gold door
- **frost_district** -- blue ice on every wall, snow over dead neon, frozen turf
- **crown_citadel** -- gilded towers, gold throne-city, the final gate

## HOW THEY DROP IN
- Save menu/handler/map art to `ecosystem/game/assets/ui/`, `assets/handlers/`, `assets/maps/<city>/`.
- Cards -> `assets/cards/<slug>.png`. Tell me when a batch is in `Websites/Download/` or the assets dir and I
  wire them (swap the CSS gradients/emoji for the painted art; route premium card/skin art to the gem tier).
- Premium painted art = the GEM tier per PRICING_STRATEGY.md (your token cost x markup, on top of base).
