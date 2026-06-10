# ALLEY KINGZ x $BCARDD -- SEEDANCE BATTLE-VIDEO PRODUCTION KIT
**Date:** 2026-06-02 | **Art Director:** Seedance lane, Everlight Hive | **Status:** Ready to generate (Mythic-first batch)
**Engine (UPDATED 2026-06-03):** **Seedance 2.0** -- the current best model (Feb 2026, image-to-video + 2K + consistent characters + multi-shot, beats Sora 2 / Veo 3.1). Use 2.0 for the NFT hero clips, not the older 1.0 Pro. KEY PIPELINE: feed each character's finished game ICON (the transparent PNG from `ecosystem/art/ART_PROMPT_PACK.md`, made in Recraft/Leonardo) into Seedance 2.0 as the **reference image (image-to-video)** so the NFT clip animates the EXACT same dog -- one character across the game icon, the card, the NFT, and the coin. 3-4s clips. (Prompts below still apply; treat them as the motion brief on top of the icon reference.)
**Pairs with:** `Alley_Kingz/ART_BIBLE.md`, `Alley_Kingz/PROMPT_BIBLE.md`, `Alley_Kingz/VISUAL_AI_PIPELINE_SOP.md`, `MASTER_ECOSYSTEM_PLAN_2026-06-02.md`

---

## 0. THE ONE-SENTENCE BRIEF (read this, then generate)

> Cyberpunk dog crews pilot Twisted-Metal street war-rigs down Clash-Royale lanes, charging neon-night and golden-hour boulevards, muzzle-flash and nitro and debris, ramming towers until the towers collapse downhill. $BCARDD -- the Dogo Argentino warlord who is the $BCARDD coin AND the blackjack dealer -- rides a crowned matte-black war-rig with gold trim. One dog, one currency, one aesthetic, one arcade.

Reference feel: **Twisted Metal 3/4 (PlayStation) crossed with Clash Royale lanes.** Hyper-real PBR per ART_BIBLE.md. Premium, never cartoonish.

### LOCKED PALETTE (every clip carries at least 2 of these)
| Name | Hex | Use in battle clips |
|------|-----|---------------------|
| Crown Gold | `#D4AF37` (gradient partner `#c9a84c`) | $BCARDD trim, faction crowns, win-glow, Mythic auras |
| Vanta Black | `#050507` | Coin-art base, deep shadow, $BCARDD rig body |
| Midnight Deep | `#0D0D1A` | Night-lane backgrounds, shadow fill |
| Neon Cyan | `#00F5FF` | Nitro trails, skill FX, headlights, Zoomie faction |
| Brick Warm | `#C1440E` | Muzzle-flash, ember, tower-collapse fire, Boneguard faction |
| Asphalt Grey | `#4A4A55` | Streets, lane surface, Common rigs |
| Blood Orange | `#FF4500` | Damage hits, explosion cores (accent only) |

### UNIVERSAL SEEDANCE TAGS -- append to EVERY prompt below
`hyper-real PBR materials, cinematic depth of field, volumetric haze, physically-based lighting, photoreal motion blur, 24fps cinematic, loop-ready seamless, ultra-detailed 4K render`

### UNIVERSAL NEGATIVE -- append to EVERY prompt
`no text, no watermark, no signature, no logo overlay, no UI, no subtitles, low quality, blurry, 2D sprite, pixel art, flat shading, cartoon, anime, oversaturated, extra limbs, deformed dog anatomy, rum bottle, liquor branding`

> The "no rum bottle / no liquor" negative is a HARD coin rule from `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`: $BCARDD is clearly the DOG, never the drink.

### THE FOUR FACTIONS -> RIG LANGUAGE (so every clip reads its crew at a glance)
- **Boneguard Crew** ($BCARDD, Stonejaw): heavy armored brawler rigs -- bull-bars, riveted plate, brick-warm `#C1440E` war-paint over matte black. Tanky, low, wide.
- **Zoomie Syndicate** (Jagged): low-slung neon-cyan `#00F5FF` speed rigs -- exposed turbines, light frames, blade-thin, built to dash and crit.
- **Leashbreak Tactix** (Rosco): hacker tech-rigs -- antenna arrays, holographic dish, cyan glyph projectors, EMP emitters. Disables towers.
- **K9 Circuitry** (Crown Foxhound): chrome turret-rigs / drone-carriers -- rail-cannons, drone bays, polished chrome and gold. Structure-breakers.

---

## 1. CHARACTER LIST -- VISUAL DESCRIPTIONS (priority set)

### THE 4 MYTHICS (generate first -- the hype set)

**#0001 -- BCARDD** *(Dogo Argentino, Boneguard Crew, Vanguard, "Crownbreaker", HP 2600)*
A pure-white short-coat Dogo Argentino warlord, scarred muscular chest, one cropped ear, intelligent amber eyes -- the SAME dog as the $BCARDD coin art (`Official_BCARDI.png`) and the blackjack dealer. Cyberpunk gear: a thin gold-filigree crown fused to a matte-black combat harness, gold knuckle-plates on the paws, a chest sigil that matches the coin. He pilots the **CROWNBREAKER** -- a crowned matte-black armored war-rig (`#050507` body) with hand-laid Crown Gold (`#D4AF37`) trim running the panel seams, a gold-tipped bull-bar ram, a literal welded crown over the cab, twin exhaust stacks, brick-warm war-paint scoring. This is the hero asset; its color story IS the coin's color story (vanta black + gold), so the NFT, the coin, and the dealer all rhyme.

**JAGGED** *(Doberman, Zoomie Syndicate, Assassin, "Shadow Fang", HP 1400 / DMG 210)*
A lean black-and-rust Doberman, clipped ears, glowing cyan optic-implant over one eye, carbon-fiber speed harness, exposed sinew of a sprinter. Faction colors: Neon Cyan (`#00F5FF`) glow lines on jet-black. He pilots the **SHADOW FANG** -- a low-slung blade-thin interceptor rig, exposed turbine intakes venting cyan heat-haze, two retractable energy-fangs on the nose, phase-shimmer cloaking panels. Built to dash a lane and teleport-strike the enemy Queen.

**ROSCO** *(Australian Cattle Dog, Leashbreak Tactix, Controller, "Leashbreak", HP 1800)*
A blue-merle Australian Cattle Dog, alert pricked ears, speckled grey-and-tan coat, a tactical visor projecting a cyan HUD across his eyes. Cyberpunk gear: a back-mounted antenna rig, glyph-projector collar, fingerless-style grip wraps on the forepaws. He pilots the **LEASHBREAKER** -- a tech command-rig bristling with a rotating holographic dish, cyan EMP emitter arms, and a roof of antenna spines that fire a "leash-cut" pulse that visibly kills a tower's lights/turret. Disables structures; can target the Queen.

**CROWN FOXHOUND** *(Foxhound, K9 Circuitry, Assassin, "Royal Hunt", HP 1600 / DMG 200)*
A regal tri-color American Foxhound, tall and lean, a slim gold circlet between the ears, polished-chrome cyber-spine running the back, gold-and-cyan optic. Faction colors: chrome + Crown Gold. He pilots the **ROYAL HUNT** -- a chrome-plated turret-rig with a long gold-tipped rail-cannon spine, drone-bay flanks, hunter-green targeting lasers. The structure-breaker: it locks onto towers and the Queen and punches holes through plating.

### THE LEGENDARY (hero treatment, after the Mythics)

**STONEJAW** *(Mastiff, Boneguard Crew, Vanguard, "Armor Pulse", HP 2100)*
A massive fawn English Mastiff, jowled and immovable, battle-scarred muzzle, slow burning confidence. Cyberpunk gear: a riveted iron pauldron-harness, a reinforced jaw-guard, brick-warm faction war-paint. He pilots the **STONEWALL** -- the heaviest brawler rig in the game: a slab-sided matte-black tank-truck with a brick-warm (`#C1440E`) plow blade, rivet-studded armor skirts, and a pulsing amber "Armor Pulse" aura dome that visibly hardens nearby allied rigs. The wall the lane breaks against.

> NOTE on roster: `cards.json` lists exactly **4 Mythics + 1 Legendary (Stonejaw)**. The other 8 top-of-ladder cards are Epic. The Epic hero-shorts batch (Balboa, Iron Rottweiler, Razor Vizsla, Aero Malinois, Synth Collie, Noir Setter, Circuit Retriever, Nova Shepherd) is specced in Section 5 so the priority set above stays tight and on-budget.

---

## 2. READY-TO-PASTE SEEDANCE PROMPTS -- PRIORITY CHARACTERS (3-4s battle loops)

Copy a block, append the **UNIVERSAL SEEDANCE TAGS** and the **UNIVERSAL NEGATIVE** from Section 0, generate at the noted aspect ratio. Each is a single 3-4s loop-ready clip (~300 credits).

### 2.1 BCARDD -- "CROWNBREAKER RAM" (hero clip, 16:9)
```
Cinematic low tracking shot chasing a crowned matte-black armored war-rig (vanta black #050507 body,
hand-laid Crown Gold #D4AF37 trim along every panel seam, a welded gold crown bolted over the cab,
gold-tipped bull-bar ram) as a pure-white scarred Dogo Argentino warlord with a thin gold crown-harness
grips the wheel, amber eyes locked forward. The rig nitro-boosts down a wet neon-night cyberpunk
boulevard, gold sparks streaming off the bull-bar, brick-warm muzzle-flash from a roof cannon. It slams
head-on into a glowing enemy lane tower -- the tower cracks, gold and blood-orange #FF4500 debris
explodes outward, the structure buckles and begins to topple downhill. Camera shakes on impact. Neon
cyan #00F5FF and gold reflections shimmer in the wet asphalt. Golden-hour rim light meets neon-night
shadow. 16:9.
```

### 2.2 BCARDD -- "COIN-TIE THRONE IDLE" (loop, square, for arcade + coin cross-promo)
```
Slow cinematic dolly-in on the same crowned matte-black war-rig idling at the top of a cyberpunk lane,
engine pulsing, twin exhaust stacks venting heat-haze. The white Dogo Argentino warlord $BCARDD stands
in the open turret hatch, gold crown-harness catching a single overhead gold key-light, the chest sigil
glinting exactly like the $BCARDD coin face. Gold #D4AF37 light rakes across the matte black #050507
hull, embers drift, a faint gold dust halo. Pure vanta-black background so the rig and dog read as the
coin mascot. Regal, still, menacing. Seamless loop, premium product-shot energy. Square 1:1.
```

### 2.3 JAGGED -- "SHADOW FANG DASH-STRIKE" (16:9)
```
Fast whip-pan following a low-slung blade-thin neon-cyan interceptor rig (#00F5FF glow lines on jet
black, exposed turbines venting cyan heat-haze, two energy-fangs on the nose) as a lean black-and-rust
Doberman with a glowing cyan optic-implant pilots it at full dash. The rig phase-shimmers, cloaking
panels flickering, then teleport-blinks forward in a streak of cyan light and lunges the energy-fangs
into the base of a tall enemy tower. Cyan shockwave, sparks, the tower's lights flicker and die. Motion
blur on the lane, neon signage streaking past. Deep midnight-blue #0D0D1A night, cyan rim light.
Loop-ready. 16:9.
```

### 2.4 ROSCO -- "LEASHBREAKER EMP PULSE" (16:9)
```
Medium tracking shot of a tech command-rig (matte black with cyan glyph projectors, a rotating
holographic dish on the roof, antenna spines, EMP emitter arms) rolling into a Clash-Royale-style lane
as a blue-merle Australian Cattle Dog in a cyan HUD visor works the controls. The roof dish spins up and
fires a wide cyan "leashbreak" EMP pulse #00F5FF that washes over an enemy lane tower -- the tower's
turret droops, its glowing lights short out and go dark, electric arcs crawl over its plating. Holographic
cyan glyphs ripple outward across the wet street. Neon-night, volumetric cyan haze, gold #D4AF37 accent
on the rig's edge. Loop-ready. 16:9.
```

### 2.5 CROWN FOXHOUND -- "ROYAL HUNT RAIL-SHOT" (16:9)
```
Cinematic side-tracking shot of a chrome-plated turret-rig with a long gold-tipped rail-cannon spine
(polished chrome + Crown Gold #D4AF37, drone-bay flanks, hunter-green targeting lasers) driven by a
regal tri-color Foxhound with a thin gold circlet and a cyber-spine. The rail-cannon charges with a
building gold glow, hunter-green laser locks onto a distant enemy tower, then FIRES -- a gold rail-slug
punches clean through the tower's plating, blood-orange #FF4500 explosion blooms, drones launch from the
flank bays into the smoke. Recoil rocks the rig. Golden-hour light glints off chrome. Loop-ready. 16:9.
```

### 2.6 STONEJAW -- "STONEWALL ARMOR PULSE" (Legendary, 16:9)
```
Heavy slow-push camera on the bulkiest rig in the lane: a slab-sided matte-black tank-truck with a
brick-warm #C1440E plow blade, rivet-studded armor skirts, piloted by a massive scarred fawn Mastiff in
an iron pauldron-harness. The rig grinds forward absorbing incoming brick-warm muzzle-flash that sparks
harmlessly off its plate, then slams its plow into a barricade, debris scattering. A pulsing amber
"Armor Pulse" energy dome expands from the rig, visibly hardening two allied rigs beside it with a gold
#D4AF37 shimmer. Immovable, grinding, dust and embers. Neon-night with brick-warm fill light. Loop-ready. 16:9.
```

---

## 3. WAR-TRAILER BATCH -- 5 CINEMATIC CREW-vs-CREW / RIG-vs-TOWER CLIPS

This is Rich's "going to war / shooting each other / towers go down" set: the launch teaser, the arcade hero loop, and social cut-downs. All 16:9, 3-4s, ~300 credits each. Append the universal tags + negative. Cut them in this order for a ~15-20s trailer.

### T1 -- "THE LANES IGNITE" (establishing, cold open)
```
Sweeping cinematic crane shot rising over a cyberpunk city at neon-night, revealing three Clash-Royale-style
lanes carved into wet neon streets, glowing towers standing at each end. Down every lane, packs of armored
dog war-rigs rev and stage at the line -- matte-black Boneguard tanks with gold trim, cyan Zoomie speed rigs,
chrome K9 turret rigs. Headlights snap on in sequence, nitro flares ignite, gold #D4AF37 and cyan #00F5FF
light floods the wet asphalt. The calm before the charge. Volumetric fog at the intersections. 16:9.
```

### T2 -- "THE CHARGE" (rising action)
```
Low fast tracking shot down a center lane as a full pack of dog-piloted war-rigs charges at speed -- $BCARDD's
crowned matte-black Crownbreaker leading with gold sparks off the bull-bar, a cyan Doberman interceptor and a
chrome Foxhound turret-rig flanking. Nitro trails streak cyan and gold, debris kicks up, motion blur on the
neon signage. Brick-warm #C1440E muzzle-flash erupts from roof cannons as they open fire on the enemy line
ahead. Camera low to the asphalt, kinetic, cinematic. Neon-night, wet reflections. 16:9.
```

### T3 -- "CROSSFIRE" (crew vs crew -- the shootout)
```
Cinematic mid-shot of two dog war-rig crews trading fire across a cyberpunk intersection. Brick-warm and
blood-orange #FF4500 muzzle-flashes strobe, tracer rounds and cyan #00F5FF energy bolts cross the frame,
sparks rain off armor plating as rounds hit. A Zoomie speed rig drifts sideways through the crossfire firing,
a Boneguard tank rig grinds forward absorbing hits. Shell casings and gold debris litter the wet street.
Smoke, embers, lens-flare off the neon. War, vehicular, hyper-real. 16:9.
```

### T4 -- "TOWER FALLS" (the payoff -- towers go down)
```
Dramatic low hero-angle as $BCARDD's crowned matte-black Crownbreaker rig, gold #D4AF37 trim blazing,
rams the base of a towering enemy lane structure at full nitro. The tower's plating shatters, gold and
blood-orange #FF4500 explosion blooms from the impact, structural beams snap, and the entire tower
buckles and topples DOWNHILL in slow-motion, crushing debris cascading down the sloped neon street toward
camera. Shockwave dust, flying sparks, fire glow. Epic, cinematic, the money shot. 16:9.
```

### T5 -- "KING OF THE PACK" (logo-beat / coin tie-in, hold for end card)
```
Slow heroic dolly-up on $BCARDD the white Dogo Argentino warlord standing in the turret hatch of his
crowned matte-black gold-trimmed war-rig atop the rubble of a fallen tower, smoke and gold embers
drifting, a single gold #D4AF37 key-light raking his crown-harness and chest sigil so it reads exactly
like the $BCARDD coin. His pack of rigs idles behind him in silhouette. Pure vanta-black #050507 sky.
Regal, victorious, the last frame before the end card. Seamless slow loop. 16:9.
```

**Trailer assembly note:** render at 16:9; the arcade hero loop uses T1+T5 (calm-to-king) on a seamless cut; social cut-downs use T2/T3/T4 as standalone 3-4s vertical-safe crops (keep action center-framed so a 9:16 crop survives).

---

## 4. PHASED CREDIT BUDGET (free-first gated)

**FREE-FIRST NOTE (do this BEFORE any bulk spend):** Confirm the live Seedance credit balance first. Per the Blackjack precedent, video = ~300 credits each; the only real spend in this whole ecosystem is Seedance credits + the $BCARDD dev-buy (everything else reuses existing infra: e5-mother render path, Cloudflare, the Unity/HTML prototypes, the art/prompt bibles). Do NOT batch-buy the full 50. Gate each phase on what the launch + game actually need, and route the Art Review Gate (`VISUAL_AI_PIPELINE_SOP.md` Stage 4) on every clip before it ships. No AI slop.

| Phase | Scope | Clips | Est. Credits | Trigger to spend |
|-------|-------|-------|--------------|------------------|
| **Batch 1 -- MYTHIC HYPE SET** | 4 Mythic hero clips (2.1, 2.3, 2.4, 2.5) + 1 $BCARDD coin-tie idle (2.2) | 5 | ~1,500 | Coin-launch teaser + NFT preview. *Trim to the 4 Mythics (~1,200) if balance is tight; 2.2 is the highest-value add-on for coin cross-promo.* |
| **Batch 1b -- WAR TRAILER** | 5 trailer clips (T1-T5) | 5 | ~1,500 | The launch teaser + arcade hero loop + social. Can run same session as Batch 1. |
| **Batch 2 -- LEGENDARY + TOP EPICS** | Stonejaw (2.6) + 8 Epic hero-shorts (Balboa, Iron Rottweiler, Razor Vizsla, Aero Malinois, Synth Collie, Noir Setter, Circuit Retriever, Nova Shepherd) | 9 | ~2,700 | After Mythics land + game build needs more cards animated. |
| **Batch 3 -- RARE TAIL** | ~18 Rare cards, shorter 3s clips | 18 | ~5,400 | Marketplace depth, phased. |
| **Batch 4 -- COMMON TAIL** | ~14 Common cards, batch 3s clips | 14 | ~4,200 | Full-set completion only when demand justifies. |
| **FULL SET TOTAL (all 50 + trailer)** | every card video + trailer | ~55 | **~16,500** | NEVER all at once. Phase strictly. |

**Recommended default (Art Director's call):** Fund **Batch 1 + Batch 1b together = ~3,000 credits** -> that delivers the 4 Mythic hero clips + $BCARDD coin-tie idle + the full 5-clip war trailer. That is the entire launch-and-hype kit (coin teaser, NFT preview, arcade hero loop, social) in one sitting. Everything past that is gated on the game build and marketplace demand. Confirm balance first; if it cannot cover ~3,000, drop 2.2 and run the 4 Mythics + 5 trailer clips (~2,700), or Mythics-only (~1,200) as the floor.

---

## 5. EPIC HERO-SHORTS (Batch 2 reference -- prompt spines, generate after Mythics)

Same universal tags + negative, 16:9 unless noted, ~300 credits each. One-line action spines (expand to full prompts at generation time using the Section 2 pattern + the faction rig language in Section 0):

- **Balboa** (Boxer, Boneguard, "Haymaker"): brick-warm brawler rig rams a rig and stuns it with a haymaker-impact shockwave, opponent rig rocks back.
- **Iron Rottweiler** (Rottweiler, Boneguard, "Overclock Rage"): battered matte-black rig below 40% HP venting red overclock steam, gold-red rage glow, charges harder.
- **Razor Vizsla** (Vizsla, Zoomie, "Pierce Rush"): cyan lancer rig fires a line-piercing energy spear straight down a lane through multiple targets.
- **Aero Malinois** (Malinois, Zoomie, "Twin Strike"): cyan speed rig double-taps a tower with two rapid nitro-strikes, two cyan impact flashes.
- **Synth Collie** (Border Collie, Leashbreak, "Hack Jam"): tech rig projects a cyan hack-grid that freezes an enemy tower's fire, turret goes dark.
- **Noir Setter** (Setter, Leashbreak, "Blackout"): tech rig emits a darkness pulse that blinds ranged enemy rigs, their targeting lasers scatter.
- **Circuit Retriever** (Retriever, K9 Circuitry, "Drone Swarm"): chrome carrier rig opens its bays and launches a swarm of 5 cyan drones at a tower.
- **Nova Shepherd** (German Shepherd, K9 Circuitry, "Overclock"): chrome turret rig overclocks its rail-cannon into a burst of gold rapid-fire on a structure.

---

## 6. PIPELINE + OUTPUT HANDOFF

- **Render path:** Seedance Video 1.0 Pro. Phone proot cannot render heavy media -- if any post/compositing is needed, route to e5-mother (per master plan + proot limits).
- **Review gate (mandatory):** every clip passes `VISUAL_AI_PIPELINE_SOP.md` Stage 4 Art Review (palette has 2+ primaries, key+fill+rim lighting, hyper-real PBR, no slop) before it enters the repo. 3 fails on the same clip -> escalate to an outsource brief, do not retry-loop.
- **File naming:** `YYYY-MM-DD_AKBattle_<CharacterOrTrailerID>_Seedance_V{N}.mp4` (e.g. `2026-06-02_AKBattle_$BCARDD_Crownbreaker_Seedance_V1.mp4`).
- **Save to:** `Alley_Kingz/ecosystem/seedance_clips/` (mythics/, trailer/, epics/, rares/, commons/ subfolders), then register in `content_pack.json`.
- **NFT binding:** each character clip becomes that card's `animation_url` (the `nft_metadata_template.json` already supports `animation_url` + on-chain stats). One clip = one animated NFT = one playable card. $BCARDD's clip ties the coin, the NFT, the dealer, and the card to the SAME dog and the SAME vanta-black-and-gold color story.
- **Cross-promo use:** T1+T5 = arcade hero loop on the website; T2/T3/T4 = social teasers; 2.2 ($BCARDD coin-tie idle) = pump.fun / X / Telegram coin-launch asset alongside the existing `BCARDI_OFFICIAL_COIN.mp4`.

---

*Battle Kit v1.0 -- 2026-06-02. Built on the proven Seedance Blackjack precedent. Generate Batch 1 + 1b first (~3,000 credits, balance-confirmed), gate the rest. One dog, one currency, one aesthetic, one arcade.*
