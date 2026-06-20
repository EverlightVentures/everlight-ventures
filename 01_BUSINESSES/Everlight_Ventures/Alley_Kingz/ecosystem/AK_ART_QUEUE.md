# ALLEY KINGZ -- ART GENERATION QUEUE (ready-to-run; 2026-06-19)
> Prioritized, copy-paste generation queue for the master plan. Feeds the art factory
> (Leonardo bulk -> CF Workers AI failover) + Seedance (premium hero, manual/operator).
> Canon: AK_ART_PORTFOLIO.md (palette + style + routing) + AK_WORLD_BIBLE.md (NeonReach
> world + 10 archetypes + 6 ascension tiers) + AK_MASTER_BLUEPRINT.md + ALLEY_KINGZ_TODO.md.
> HARD: crew (never clan), graffiti (never runes), Alley Kingz (with Z). Readable by
> silhouette alone; readable at 64x64 (icons) and 200x200 (chars); one cohesive universe.

---

## 0. HOW TO RUN (the pattern, once)

Run everything from the ecosystem dir:
`/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem`

Enqueue pattern (appends to `_state/ak_art_queue.json`, the highest-priority lane):
```
python3 art/art_factory.py --enqueue \
  --id <UNIQUE_ID> \
  --prompt "<FULL PROMPT>" \
  --out  <game/assets/.../file.png> \
  --neg  "<negative prompt>" \
  --w 768 --h 768
```
Then drain the queue (Leonardo first, fails over to Cloudflare Workers AI):
```
LEONARDO_API_KEY=xxx CF_AI_TOKEN=xxx python3 art/art_factory.py --limit 12
```
- `--out` paths starting with `game/` / `assets/` / `data/` resolve under the ecosystem;
  a bare filename lands in `game/assets/cards/`. Queue drains BEFORE cards before maps.
- Square (`--w == --h`) routes CF to flux-schnell; non-square routes CF to SDXL. Icons/auras
  square; facades portrait; interiors/design-sheets landscape.
- The daily cron `art_factory_cron.sh` (15:17 UTC, `--limit 12`) already drains this same queue.

### Palette + finish tokens (paste these as shell vars for the batch loops below)
```
NEON="NeonReach palette: Electric Purple #8B5CF6, Neon Cyan #06B6D4, Hot Pink #EC4899, Graffiti Orange #F97316, Toxic Green #22C55E, Street Gold #EAB308, Asphalt #1C1917, Concrete #78716C, Brick #991B1B"
FINISH="stylized premium cartoon-strategy game art, Clash-of-Clans readability x Brawl-Stars attitude, gritty urban-fantasy street edge, recognizable by silhouette alone, clean and readable at small sizes, vibrant saturated, one cohesive NeonReach universe, NOT kiddish, game asset, Unity-ready"
```

### PIPELINE NOTE -- the gritty auto-tail (read once)
`art_factory.py --enqueue` auto-appends the house "gritty TV-MA / Twisted-Metal, Everlight
gold #D4AF37 on vanta-black, NOT kiddish, NOT cartoonish" tail unless the prompt already ends
with it. For these NeonReach assets that tail is a FEATURE, not a bug: the NeonReach hex codes
in the prompt hold the palette while the grit-tail lifts the render from kiddish to premium
(operator law: "NOT kiddish"). Leave auto-append ON. The only thing to watch is "flat 2d" /
"chibi" creeping in -- the per-asset `--neg` below already blocks that.

### ROUTE LEGEND
- **L = Leonardo bulk** (cheap API via art_factory; CF Workers AI failover). Volume: environments,
  building tiers, props, icons, auras, alt-skins, locked silhouettes.
- **S = Seedance hero** (operator, manual, premium credits). The 10-second-hook pieces: Main Tower
  Crown tier, the 3 world-map hero shots, the 10 archetype master design-sheets, key cinematics.
  Route: generate the L base first so nothing blocks; Seedance re-paints the hero on credit re-up.

---

## PRIORITY P0 -- VERTICAL SLICE (AK_ART_PORTFOLIO Phase 1)

### P0.1 World maps -- 3 districts (the overworld you walk)  [L base + S hero]
Leonardo base plate at 1024x1024 (upscale/Seedance for the 2000px+ final hero shot).
```
python3 art/art_factory.py --enqueue --id map_core_district \
  --prompt "Isometric 3D urban overworld map, NeonReach Core District 'Where It All Starts', Downtown-LA x Tokyo-Shibuya x Brooklyn-graffiti night streets, neon signs Electric Purple #8B5CF6 + Neon Cyan #06B6D4, graffiti brick walls, wet asphalt reflecting light, steam manholes, glowing vendor carts, police drones, hidden alley doorways, a tall central Main Tower with a pulsing neon crown visible from anywhere, Clash-of-Clans-but-grittier, clean readable silhouettes, vibrant saturated, NeonReach palette" \
  --out game/assets/maps/world/core_district.png --w 1024 --h 1024 \
  --neg "no characters, no units, no UI, no text, no watermark, low quality, blurry, flat 2d"

python3 art/art_factory.py --enqueue --id map_outskirts \
  --prompt "Isometric 3D urban overworld map, NeonReach The Outskirts 'Where the Tough Survive', Detroit-factories x Mumbai-Dharavi x Berlin-industrial, fight-pit factory, scrap yard with magnetic cranes, toxic green #22C55E pools, tunnels, black market stalls, beast arena, a massive impenetrable BARRIER wall at the edge, rust + Graffiti Orange #F97316 + Toxic Green neon, grimy but readable, Clash-of-Clans-but-grittier, vibrant saturated, NeonReach palette" \
  --out game/assets/maps/world/outskirts.png --w 1024 --h 1024 \
  --neg "no characters, no units, no UI, no text, no watermark, low quality, blurry, flat 2d"

python3 art/art_factory.py --enqueue --id map_neon_abyss \
  --prompt "Isometric 3D urban overworld map, NeonReach The Neon Abyss 'Where Kings Are Crowned', Dubai x Seoul-Gangnam x Times-Square x Blade-Runner-2049, glass towers with holo-ads, glass sky bridges, a floating Sky Arena, holo-billboards, a gold VIP district, an Ascension Temple, Street Gold #EAB308 + Electric Purple #8B5CF6 + Hot Pink #EC4899, opulent and vertical, Clash-of-Clans-but-grittier, vibrant saturated, NeonReach palette" \
  --out game/assets/maps/world/neon_abyss.png --w 1024 --h 1024 \
  --neg "no characters, no units, no UI, no text, no watermark, low quality, blurry, flat 2d"
```

### P0.2 Locked-district silhouettes -- the "coming soon" obsession hooks  [L]
Bitcoin-Miner DNA: tantalizing dark teasers behind a countdown. Pure silhouette + glow.
```
python3 art/art_factory.py --enqueue --id map_locked_docks \
  --prompt "Dark teaser silhouette of a locked NeonReach district 'The Docks', backlit cargo cranes + container stacks + harbor piers as a black silhouette against a faint Neon Cyan #06B6D4 + Street Gold #EAB308 horizon glow, heavy fog, mysterious, COMING SOON tease, mostly shadow with rim-light edges, NeonReach palette" \
  --out game/assets/maps/locked/docks_silhouette.png --w 1024 --h 1024 \
  --neg "no text, no UI, no characters, fully lit, low quality, watermark, blurry"

python3 art/art_factory.py --enqueue --id map_locked_undercity \
  --prompt "Dark teaser silhouette of a locked NeonReach district 'The Undercity', underground subway tunnels + transit pillars as a black silhouette against flickering Toxic Green #22C55E + Electric Purple #8B5CF6 underglow, dripping shadow, mysterious COMING SOON tease, rim-light edges only, NeonReach palette" \
  --out game/assets/maps/locked/undercity_silhouette.png --w 1024 --h 1024 \
  --neg "no text, no UI, no characters, fully lit, low quality, watermark, blurry"

python3 art/art_factory.py --enqueue --id map_locked_skyport \
  --prompt "Dark teaser silhouette of a locked NeonReach district 'The Skyport', floating sky platforms + airship docks + antenna spires as a black silhouette against a Hot Pink #EC4899 + Street Gold #EAB308 dawn glow, high-altitude clouds, mysterious COMING SOON tease, rim-light edges only, NeonReach palette" \
  --out game/assets/maps/locked/skyport_silhouette.png --w 1024 --h 1024 \
  --neg "no text, no UI, no characters, fully lit, low quality, watermark, blurry"
```

### P0.3 The 10 player archetypes -- avatar design sheets  [S hero; L base ok]
On-brand: stylized anthropomorphic NeonReach street-dogs ($BCARDD dog-crew DNA). Each =
design sheet front/back/side + emotion row, crew-logo patch, distinct readable silhouette.
Master sheets are the face of the game -> route S (Seedance); generate the L base first.
```
ARCH=(
"brawler:a heavy muscular tank brawler street-dog, reinforced knuckle-plates and riot pads, low wide stance, Brick #991B1B + Fire Red #EF4444 accents"
"slinger:a lean ranged slinger street-dog, twin neon slingshot-pistol rig and bandolier, mid crouch aim, Hot Pink #EC4899 accents"
"runner:a wiry scout runner street-dog, light parkour gear and glowing sneakers, sprinting pose, Neon Cyan #06B6D4 speed trails"
"fixer:a support fixer street-dog, utility vest of tools and a neon repair-wrench and med-pack, kneeling repair pose, Toxic Green #22C55E accents"
"boss:a leader boss street-dog in sharp tailored streetwear with a crown lapel pin, commanding arms-crossed pose, Street Gold #EAB308 + Electric Purple #8B5CF6"
"ghost:a stealth ghost street-dog in a hooded cloak, holographic phantom shimmer, half-transparent flicker, Electric Purple #8B5CF6 glow"
"hype:a morale hype street-dog showman, LED jacket and shoulder boombox, hands raised rallying, Graffiti Orange #F97316 accents"
"scribe:an intel scribe street-dog with an AR visor and a data-slate tablet and a tagging marker, analytic pose, Siren Blue #3B82F6 holo-glyphs"
"muscle:a tall imposing enforcer muscle street-dog bouncer, brass knuckles and a chain, crossed arms blocking, Concrete #78716C + Fire Red #EF4444"
"kid:a small scrappy rookie kid street-dog in an oversized hand-me-down hoodie holding a spray can, eager pose, Smoke White #F5F5F4 + Neon Cyan #06B6D4"
)
for a in "${ARCH[@]}"; do id="${a%%:*}"; desc="${a#*:}"; \
python3 art/art_factory.py --enqueue --id "arch_${id}" \
  --prompt "Character design sheet of ${desc}, stylized anthropomorphic urban street-dog, full body front view + back view + side view + a row of 4 facial emotions, a crew-logo patch on the chest, distinct readable silhouette, $FINISH, $NEON, transparent background" \
  --out "game/assets/avatars/${id}.png" --w 1216 --h 832 \
  --neg "extra limbs, deformed hands, blurry, low quality, watermark, text labels, chibi, flat 2d"; done
```

### P0.4 Core building exteriors -- 8 base-tier (Bronze)  [L]
The 8 Phase-1 core buildings. Bronze = starter tier (full 6-tier scope in P2.1 below).
Main Tower base ships here; the Crown-tier Main Tower hero is Seedance (P2.1).
```
BLD=(
"main_tower:the Main Tower / Crew HQ, the tallest building, a pulsing neon crown on top projecting a crew emblem, visible from anywhere"
"spell_shop:a graffiti Spell Shop storefront stocked with glowing canned graffiti-spell aerosols, Electric Purple #8B5CF6 neon sign"
"deck_lab:a Deck Lab workshop where cards are tuned, holographic card racks in the window, Neon Cyan #06B6D4 glow"
"training_grounds:a Training Grounds gym yard with sandbags, dummies and a sparring cage, Graffiti Orange #F97316 floodlights"
"crew_hall:a Crew Hall clubhouse with graffiti walls and a crew banner, stoop and roller door, Hot Pink #EC4899 neon"
"marketplace:a street Marketplace of stalls and vendor carts trading goods, Street Gold #EAB308 string lights"
"bounty_board:a Bounty Board fixer office plastered with wanted posters and a neon job ticker, Fire Red #EF4444 accents"
"shield_station:a Shield Station defense bunker with energy-shield emitters glowing on the roof, Siren Blue #3B82F6 glow"
)
for b in "${BLD[@]}"; do id="${b%%:*}"; desc="${b#*:}"; \
python3 art/art_factory.py --enqueue --id "bld_${id}_bronze" \
  --prompt "Isometric 3D building exterior of ${desc}, weathered bronze plating and dull patina trim (starter Bronze ascension tier), front-facing facade centered, readable silhouette, NeonReach Core District street architecture, $FINISH, $NEON, transparent background" \
  --out "game/assets/hub/buildings/${id}_bronze.png" --w 768 --h 1024 \
  --neg "no characters, no UI, no text, watermark, low quality, blurry, flat 2d"; done
```

### P0.5 Main HUD + currency + core iconography (UI_01)  [L]
The TIER-5 HUD set. 64x64 readability is the bar; generate at 512 square, downscale.
```
ICON=(
"cur_alk:the ALK street currency coin stamped with a crew crown emblem, Street Gold #EAB308 coin"
"cur_satoshi:a glowing Satoshi-Fragment shard, a cracked bitcoin-fragment crystal, Graffiti Orange #F97316 glow"
"cur_rep:a Crew Reputation crown icon that radiates social heat, Hot Pink #EC4899 + Street Gold #EAB308"
"hud_hp:a health HP heart-shield icon, Fire Red #EF4444"
"hud_shield:a defense shield icon with an energy ring, Siren Blue #3B82F6"
"hud_raid:a raid crossed-bats / attack icon, Brick #991B1B"
"hud_crew:a crew roster / squad-of-three icon, Electric Purple #8B5CF6"
"hud_chest:an alley crate / reward chest icon, Street Gold #EAB308"
"hud_special:a tap-fired special-ability burst icon for the HUD radial button, Neon Cyan #06B6D4"
"hud_map:a world-map / overworld pin icon, Neon Cyan #06B6D4"
"hud_journal:a journal / quests log icon, Toxic Green #22C55E"
"hud_settings:a settings gear icon with a graffiti edge, Concrete #78716C"
)
for i in "${ICON[@]}"; do id="${i%%:*}"; desc="${i#*:}"; \
python3 art/art_factory.py --enqueue --id "${id}" \
  --prompt "Game UI icon, ${desc}, bold chunky readable silhouette legible at 64x64, centered single object, subtle neon rim-light, $NEON, transparent background, sticker-clean edges" \
  --out "game/assets/ui/${id}.png" --w 512 --h 512 \
  --neg "no text, no words, cluttered, busy, low contrast, blurry, watermark, photorealistic"; done
```

### P0.6 Skill-point token + skill-tree node frames  [L]
Skill-tree is live (handlers_data.js, 31 nodes); give it real node art.
```
python3 art/art_factory.py --enqueue --id skill_point_token \
  --prompt "Game UI icon, a Bones skill-point token, a glowing graffiti-tagged street-dog bone medallion, bold readable at 64x64, centered, $NEON, transparent background" \
  --out game/assets/ui/skill/skill_point.png --w 512 --h 512 \
  --neg "no text, cluttered, blurry, watermark, photorealistic"

NODE=(
"locked:a LOCKED skill node frame, a dim padlocked hexagon socket, dark Concrete #78716C with a faint glow"
"unlockable:an UNLOCKABLE skill node frame, a bright pulsing hexagon socket ready to buy, Neon Cyan #06B6D4 ring"
"owned:an OWNED skill node frame, a filled hexagon socket with a lit core, Toxic Green #22C55E ring"
"maxed:a MAXED skill node frame, an ornate gold hexagon socket with a crown spark, Street Gold #EAB308 radiant ring"
)
for n in "${NODE[@]}"; do id="${n%%:*}"; desc="${n#*:}"; \
python3 art/art_factory.py --enqueue --id "skillnode_${id}" \
  --prompt "Game UI element, ${desc}, empty center for an inset glyph, bold readable at 96x96, centered hexagon, $NEON, transparent background" \
  --out "game/assets/ui/skill/node_${id}.png" --w 512 --h 512 \
  --neg "no text, no inner icon, cluttered, blurry, watermark, photorealistic"; done
```

### P0.7 Squad role auras -- the ground rings under units  [L]
Top-down transparent ground-rings. Two families: combat-role auras + crew-strategy auras
(the daily-rotating strategy reskins the crew UI -- Aggressive/Defensive/Economic/Diplomatic).
```
AURA=(
"role_tank:a tank role aura, a heavy Brick #991B1B shield-ring with armor notches"
"role_ranged:a ranged role aura, a Hot Pink #EC4899 crosshair-ring with range ticks"
"role_scout:a scout role aura, a Neon Cyan #06B6D4 dashed speed-ring"
"role_support:a support role aura, a Toxic Green #22C55E pulsing heal-ring"
"role_leader:a leader role aura, a Street Gold #EAB308 crown-ring"
"role_stealth:a stealth role aura, an Electric Purple #8B5CF6 phantom-ring, half-faded"
"strat_aggressive:an AGGRESSIVE crew-strategy aura, a Fire Red #EF4444 jagged high-risk ring"
"strat_defensive:a DEFENSIVE crew-strategy aura, a Siren Blue #3B82F6 solid bulwark ring"
"strat_economic:an ECONOMIC crew-strategy aura, a Toxic Green #22C55E coin-flecked ring"
"strat_diplomatic:a DIPLOMATIC crew-strategy aura, an Electric Purple #8B5CF6 treaty ring"
)
for u in "${AURA[@]}"; do id="${u%%:*}"; desc="${u#*:}"; \
python3 art/art_factory.py --enqueue --id "aura_${id}" \
  --prompt "Top-down circular ground aura VFX ring for a game unit, ${desc}, glowing neon ring on the ground, empty transparent center, soft outer falloff, $NEON, transparent background, seen from above" \
  --out "game/assets/specials/auras/${id}.png" --w 512 --h 512 \
  --neg "no characters, no unit, no text, filled center, square edges, blurry, watermark"; done
```

---

## PRIORITY P1 -- BETA DEPTH (AK_ART_PORTFOLIO Phase 2)

### P1.1 Core building INTERIORS -- 8 rooms  [L]
You walk INTO these from the hub. Landscape room shots.
```
INT=(
"main_tower:the Main Tower Crew HQ war-room interior, a central holo-table of the district map, crew banners, command screens"
"spell_shop:the Spell Shop interior, shelves of glowing canned graffiti-spells, a vendor counter"
"deck_lab:the Deck Lab interior, holo card-tuning benches and a card-evolution rig"
"training_grounds:the Training Grounds interior, sparring cages, sandbags, a beast dummy"
"crew_hall:the Crew Hall interior, couches, a trophy shelf, graffiti walls, a crew-chest in the corner"
"marketplace:the Marketplace interior, trading stalls and a marketplace ledger board"
"bounty_board:the Bounty Board interior, a wall of wanted posters and a job ticker desk"
"shield_station:the Shield Station interior, glowing energy-shield emitters and a control console"
)
for r in "${INT[@]}"; do id="${r%%:*}"; desc="${r#*:}"; \
python3 art/art_factory.py --enqueue --id "int_${id}" \
  --prompt "Isometric 3D interior room of ${desc}, NeonReach street-cyberpunk decor, warm neon practicals, readable game-room layout, $FINISH, $NEON" \
  --out "game/assets/interiors/${id}.png" --w 1024 --h 768 \
  --neg "no characters, no UI, no text, watermark, low quality, blurry, flat 2d"; done
```

### P1.2 Faction-themed cosmetic SKINS -- alt-art per archetype  [L]
The Drip layer. In-match cosmetic = a 2D alt-art swap (Fortnite layer). 4 faction reskins
per archetype (Crowned / Rusted / Hologhosts / Unbound). Reuses the P0.3 base pose.
```
FAC=(
"crowned:The Crowned faction skin, gold-and-diamond elite regalia, arrogant, Street Gold #EAB308 + white diamond"
"rusted:The Rusted faction skin, scavenged rust-metal and neon-green underdog gear, Toxic Green #22C55E + rust"
"hologhost:The Hologhosts faction skin, holographic phantom translucency and glitch-tech, Electric Purple #8B5CF6 + Neon Cyan #06B6D4"
"unbound:The Unbound faction skin, raw basic street gear, hungry rookie look, Concrete #78716C + Graffiti Orange #F97316"
)
for id in brawler slinger runner fixer boss ghost hype scribe muscle kid; do \
 for f in "${FAC[@]}"; do fid="${f%%:*}"; fdesc="${f#*:}"; \
 python3 art/art_factory.py --enqueue --id "skin_${id}_${fid}" \
  --prompt "Character cosmetic skin, the ${id} archetype street-dog wearing ${fdesc}, same readable silhouette and pose as the base archetype, single full-body front view, $FINISH, $NEON, transparent background" \
  --out "game/assets/cosmetics/skins/${id}_${fid}.png" --w 768 --h 1024 \
  --neg "extra limbs, deformed, blurry, low quality, watermark, text, chibi, flat 2d"; done; done
```

### P1.3 Cosmetic props -- sprays, trails, rig skins, emote tags  [L]
```
COS=(
"spray_crown:a graffiti spray-tag of a dripping crown, Street Gold #EAB308"
"spray_skull:a graffiti spray-tag of a street-dog skull, Hot Pink #EC4899"
"spray_bcardd:a graffiti spray-tag of the $BCARDD crowned-B card device, Electric Purple #8B5CF6"
"trail_neon:a ground movement trail cosmetic, a ribbon of Neon Cyan #06B6D4 light"
"trail_flame:a ground movement trail cosmetic, Graffiti Orange #F97316 street-fire"
"rigskin_chrome:a vehicle/rig paint-skin swatch, mirror chrome with Neon Cyan #06B6D4 pinstripe"
"rigskin_gold:a vehicle/rig paint-skin swatch, gilded Street Gold #EAB308 with diamond flecks"
"emote_mic_drop:an emote pictogram, a mic-drop celebration, Hot Pink #EC4899"
)
for c in "${COS[@]}"; do id="${c%%:*}"; desc="${c#*:}"; \
python3 art/art_factory.py --enqueue --id "cos_${id}" \
  --prompt "Game cosmetic asset, ${desc}, single centered object, readable silhouette, $NEON, transparent background" \
  --out "game/assets/cosmetics/${id}.png" --w 768 --h 768 \
  --neg "no text, cluttered, blurry, watermark, photorealistic, flat 2d"; done
```

### P1.4 Alley crates + barriers + crew-strategy UI banners  [L]
Bitcoin-Miner DNA props (AK_WORLD_BIBLE).
```
CRATE=(
"crate_wooden:a common Wooden alley crate, splintered planks, faint glow, Concrete #78716C"
"crate_metal:a rare Metal alley crate, riveted steel with a Siren Blue #3B82F6 lock"
"crate_neon:an epic Neon alley crate, glowing Electric Purple #8B5CF6 + Hot Pink #EC4899 trim"
"crate_golden:a legendary Golden alley crate, radiant Street Gold #EAB308 with a crown clasp"
"barrier_bridge:a Collapsed Bridge district barrier, broken span, impassable, IMPENETRABLE look"
"barrier_blockade:a Gang Blockade district barrier, stacked wrecks and graffiti, IMPENETRABLE"
"barrier_checkpoint:a Police Checkpoint district barrier, drone-lit gate and barricades, IMPENETRABLE"
"barrier_ward:a Magical Ward district barrier, a shimmering graffiti energy wall, IMPENETRABLE"
)
for c in "${CRATE[@]}"; do id="${c%%:*}"; desc="${c#*:}"; \
python3 art/art_factory.py --enqueue --id "${id}" \
  --prompt "Game prop, ${desc}, single centered object, readable silhouette, NeonReach street-cyberpunk, $NEON, transparent background" \
  --out "game/assets/props/${id}.png" --w 768 --h 768 \
  --neg "no characters, no UI, no text, watermark, blurry, flat 2d"; done
```

---

## PRIORITY P2 -- THE 6-TIER ASCENSION SCOPE (massive; AK_WORLD_BIBLE prestige)

> ART SCOPE (non-negotiable per AK_WORLD_BIBLE): 6 visual tiers for EVERY building, card
> frame, and crew emblem. Bronze -> Silver -> Gold -> Platinum -> Diamond -> Crown. The
> Crown tier of the Main Tower + the 4 faction crew emblems at Crown are Seedance hero (S).
> Everything else is Leonardo bulk (L). This is the single biggest queue -- gate it after P0/P1.

### Tier modifier table (paste as the `TIER` array)
```
TIER=(
"bronze:weathered bronze plating and dull patina, simple banner, humble starter tier"
"silver:polished silver trim and brighter neon accents, cleaner lines, established tier"
"gold:gilded Street Gold #EAB308 trim with a small glowing crown motif, ornate, respected tier"
"platinum:platinum-white chrome with Neon Cyan #06B6D4 energy lines, sleek hi-tech, elite tier"
"diamond:faceted diamond inlays with prismatic refraction and an Electric Purple #8B5CF6 aura, feared tier"
"crown:a full royal crown structure, radiant gold and diamond, a Hot Pink #EC4899 + Street Gold #EAB308 energy storm, max-prestige throne tier"
)
```

### P2.1 Buildings x 6 tiers (16 buildings x 6 = 96 facades)  [L; Main Tower Crown = S]
```
ALLBLD="main_tower spell_shop deck_lab training_grounds crew_hall marketplace bounty_board shield_station spell_forge deck_evolution beast_arena black_market ascension_temple legendary_forge sky_arena creator_hub"
for id in $ALLBLD; do for t in "${TIER[@]}"; do tid="${t%%:*}"; tdesc="${t#*:}"; \
python3 art/art_factory.py --enqueue --id "bld_${id}_${tid}" \
  --prompt "Isometric 3D building exterior, the ${id//_/ } at the ${tid^^} ascension tier (${tdesc}), front-facing facade centered, the SAME readable silhouette across tiers (only the material/ornament escalates), NeonReach street architecture, $FINISH, $NEON, transparent background" \
  --out "game/assets/hub/buildings/${id}_${tid}.png" --w 768 --h 1024 \
  --neg "no characters, no UI, no text, watermark, low quality, blurry, flat 2d"; done; done
```
(Bronze rows for the 8 core buildings already enqueued in P0.4 -- the factory skips painted files.)

### P2.2 Crew emblems x 4 factions x 6 tiers (24)  [L; Crown row = S]
```
for fac in crowned rusted hologhost unbound; do for t in "${TIER[@]}"; do tid="${t%%:*}"; tdesc="${t#*:}"; \
python3 art/art_factory.py --enqueue --id "emblem_${fac}_${tid}" \
  --prompt "A crew emblem badge for the ${fac} faction at the ${tid^^} ascension tier (${tdesc}), a bold heraldic street-crew crest with a crown motif, readable at 64x64, centered, $NEON, transparent background" \
  --out "game/assets/cosmetics/emblems/${fac}_${tid}.png" --w 512 --h 512 \
  --neg "no text, cluttered, blurry, watermark, photorealistic"; done; done
```

### P2.3 Card frames x 4 rarities x 6 tiers (24)  [L]
```
for r in common rare epic legendary; do for t in "${TIER[@]}"; do tid="${t%%:*}"; tdesc="${t#*:}"; \
python3 art/art_factory.py --enqueue --id "frame_${r}_${tid}" \
  --prompt "A trading-card FRAME only (empty transparent center for the card art), ${r} rarity at the ${tid^^} ascension tier (${tdesc}), name banner at top, stats panel at bottom, a rarity gem in the corner, CCG aesthetic, $NEON, transparent center" \
  --out "game/assets/ui/frames/${r}_${tid}.png" --w 768 --h 1024 \
  --neg "no card art in center, no character, no text words, cluttered, blurry, watermark"; done; done
```

---

## PRIORITY P3 -- LAUNCH + NFT + CINEMATICS (AK_ART_PORTFOLIO Phase 3)  [mixed L/S]
- Epic + legendary card art (auto-routed via `data/card_art_manifest.json` -- the factory's
  CARDS lane already drains these new-first; nothing to hand-enqueue).
- NFT land plates (10) + skins (10) + frames (5) -> L bulk, same pattern as P2.3 / P1.2.
- Cinematics x10 (intro, faction reveals, Crown ascension, DvD war) -> **Seedance (S) only**;
  see SEEDANCE_ART_PROMPTS.md / SEEDANCE_BATTLE_KIT.md for the video kit.
- The 3 world-map HERO shots (2000/2500/3000px) -> **Seedance (S)** re-paint over the P0.1
  Leonardo base plates.

---

## QUEUE SUMMARY (counts + route + sequencing)

| Block | Assets | Route | Phase | Notes |
|---|---|---|---|---|
| P0.1 world maps | 3 | L base + S hero | P1 slice | Core / Outskirts / Neon Abyss |
| P0.2 locked silhouettes | 3 | L | P1 slice | Docks / Undercity / Skyport teasers |
| P0.3 archetypes | 10 | S hero (L base) | P1 slice | design sheets, street-dog avatars |
| P0.4 core building exteriors | 8 | L | P1 slice | Bronze tier |
| P0.5 HUD + currency icons | 12 | L | P1 slice | 64x64 readable |
| P0.6 skill token + node frames | 5 | L | P1 slice | feeds live skill tree |
| P0.7 squad role auras | 10 | L | P1 slice | 6 role + 4 strategy rings |
| P1.1 building interiors | 8 | L | beta | walk-in rooms |
| P1.2 faction skins | 40 | L | beta | 10 archetypes x 4 factions |
| P1.3 cosmetic props | 8 | L | beta | sprays/trails/rig-skins/emotes |
| P1.4 crates + barriers | 8 | L | beta | Miner-DNA props |
| P2.1 buildings x 6 tiers | 96 | L (+1 S) | prestige | 16 buildings x 6 |
| P2.2 crew emblems x tiers | 24 | L (+S Crown) | prestige | 4 factions x 6 |
| P2.3 card frames x tiers | 24 | L | prestige | 4 rarities x 6 |
| P3 NFT + cinematics + hero | ~40 | mixed | launch | cards auto-route; cinematics = Seedance |

**Totals:** ~311 hand-enqueued assets across P0-P2 (P3 cards auto-route via the manifest).
**Leonardo bulk:** ~285. **Seedance hero:** ~26 (10 archetype masters, 3 map hero shots,
Main Tower Crown, 4 Crown emblems, ~8 cinematics).

**Run order:** drain P0 (51 assets, the vertical slice) first at `--limit 12`/day; the daily
cron `art_factory_cron.sh` already drains this same `_state/ak_art_queue.json` queue, priority
queue -> cards -> maps. Gate the 144-asset P2 ascension batch behind P0+P1 so the free Leonardo
cap is spent on the slice first. Seedance hero pieces are operator-manual on credit re-up;
generate the Leonardo base of every S item first so nothing blocks on credits.

**Verify after each batch:** confirm real bytes landed (the factory never writes 0-byte stubs)
and wire into the hub (`game/assets/hub/`), then deploy ONLY from e5 `~/ak_deploy` via ship.sh
(AK sole-deployer rule). Card-art resolver is `akCardArtRel` in canon.js.
