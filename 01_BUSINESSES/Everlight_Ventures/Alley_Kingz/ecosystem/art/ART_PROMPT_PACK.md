# ALLEY KINGZ -- ART PROMPT PACK (48 Unit Icons + Card Faces + Arena Maps)
**Date:** 2026-06-03 | **Owner:** Everlight Hive / Alley Kingz art lane
**Pairs with:** `Alley_Kingz/ART_BIBLE.md`, `Alley_Kingz/PROMPT_BIBLE.md`, `ecosystem/SEEDANCE_BATTLE_KIT.md`, `ecosystem/data/cards.json`
**Purpose:** Generate custom graphics for all 48 cards + the battle arena so the operator can replace the placeholder silhouette shapes the engine currently draws.

> ONE-SENTENCE BRIEF: Cyberpunk DOG crews pilot Twisted-Metal war-rigs down Clash-Royale lanes. $BCARDD (Dogo Argentino, #0001 Mythic) is the coin + dealer + king. Gold (#D4AF37 / #c9a84c) on vanta-black (#050507), hyper-real but readable at icon scale. Four factions: Boneguard Crew (amber/brick), Zoomie Syndicate (magenta/cyan), Leashbreak Tactix (violet), K9 Circuitry (teal/chrome).

---

## 1. FORMAT + TOOL GUIDE

### 1.1 The three asset types (and the honest performance note)

| Asset | Format | Size | Why |
|-------|--------|------|-----|
| **UNIT ICON** | Transparent PNG | 256x256 | The game draws this image on the board INSTEAD of a placeholder shape. Static PNG = near-zero cost; the canvas just `drawImage()`s it. **Do NOT use MP4 here.** 48 live video sprites on a board would kill phone perf (decode + GPU thrash on a Snapdragon 665 floor). One frame, one draw. |
| **CARD FACE** | PNG portrait (or short Seedance clip) | ~512x768 (2:3) | The bigger collection/deck art. A still PNG is fine for the deck UI. A 3-4s Seedance loop is the premium NFT `animation_url` (already specced in SEEDANCE_BATTLE_KIT.md) -- play it on the card-detail screen ONLY, never 48-at-once on the board. |
| **ARENA / MAP** | Background PNG | ~540x900 portrait (board ratio) | One static background per match. Cheap. The lanes, towers, river, and units draw on top. |

**Rule of thumb:** tiny + many = static PNG (icons). Big + one-at-a-time = a clip is allowed (card face / NFT). Background = one PNG. This keeps the 60FPS floor from ART_BIBLE.md Section 8 intact.

### 1.2 Recommended tools (FREE-FIRST)

Step-2 web check (June 2026) confirms two tools nail "consistent small game-unit icons with transparent backgrounds," both with free tiers:

- **PRIMARY -- Recraft** (`recraft.ai`). Built for exactly this: a free "AI Icon Generator" / "AI Game Assets" mode that produces a SET of icons in one consistent style, exports transparent PNG **and** true vector/SVG, and has a brand-style feature so all 48 share one look. Free tier ~50 credits/day -- enough to grind the set in passes. Best when the output must behave like a design asset, not just a picture.
- **SECONDARY -- Leonardo.ai** (`leonardo.ai`). Most generous serious free tier (~150 tokens/day). Use its **Fixed Seed** + an uploaded **style/image reference** to lock the look across all 48, then its built-in **background removal** for transparency. Strongest when you want hyper-real PBR render quality matching the ART_BIBLE more than flat icon cleanliness.
- **Flux / SDXL (local or hosted free)** = fallback if you want full control / no per-day cap; pair with `rembg` or Remove.bg for the alpha cut.
- **Seedance** = NOT for the tiny icons. Reserve it for the card-face / NFT motion clips per SEEDANCE_BATTLE_KIT.md.

**How to keep all 48 consistent (the discipline that matters more than the tool):**
1. Generate ONE hero icon first ($BCARDD 0001). Approve the look.
2. **Lock the seed** (Leonardo: Copy Seed -> Fixed Seed) OR **save it as a Brand Style** (Recraft). Reuse on every subsequent card.
3. **Prepend the STYLE BIBLE LINE (Section 2) to every prompt** so palette / framing / lighting never drift.
4. Always append the **UNIVERSAL NEGATIVE**.
5. If transparency is imperfect, run the output through Remove.bg / `rembg` before saving.

### 1.3 Pipeline: generate -> upload -> AI wires it in

1. **Generate** each icon with its Section-3 prompt (Style Bible prepended, negative appended), 256x256, transparent.
2. **Cut alpha** if needed (Remove.bg / rembg) and downscale to exactly 256x256.
3. **Name + drop** per the Delivery Spec (Section 6): `ecosystem/game/assets/units/<cardNumber>_<slug>.png`.
4. **AI wires it in:** once the files exist, the engine's `drawUnit` is switched from the placeholder silhouette shapes to `ctx.drawImage(unitIcon)`, and the board renderer loads the arena PNG as the background. (Engine currently renders role-based silhouettes + a rig glyph at 18x30 tiles, two lanes, bridges at x=4/x=14, 3 towers per side = 2 princess + 1 Alpha Den king. The image swap is a drop-in.)

---

## 2. STYLE BIBLE LINE (prepend to EVERY icon prompt)

> **PREPEND -- locked style:** `Small square mobile game unit icon, hyper-real stylized PBR render (Clash Royale clarity + Uncharted 4 texture fidelity), single subject centered and readable at 60px, dynamic 3/4 battle-ready pose, cyberpunk dog crew member piloting / mounted on a Twisted-Metal war-rig. Cinematic three-point lighting (warm key, cool fill, gold rim), volumetric haze, high contrast. Everlight palette: Crown Gold #D4AF37 / #c9a84c on vanta-black #050507, with the unit's faction accent. Consistent scale and camera across the whole set, full body fitting inside the square with a small margin, transparent background.`

> **UNIVERSAL NEGATIVE -- append to EVERY icon prompt:** `no text, no letters, no numbers, no watermark, no signature, no logo overlay, no UI, no card frame, no border, no background scenery, no rum bottle, no liquor, no alcohol branding, low quality, blurry, 2D flat sprite, pixel art, flat cel shading, cartoon, anime, oversaturated, extra limbs, deformed dog anatomy, multiple subjects.`

*(The "no rum / no liquor" rule is a HARD coin law: $BCARDD is the DOG, never the drink.)*

**Faction accent quick-key (used in every prompt below):**
- **Boneguard Crew** -- amber + Brick Warm `#C1440E` war-paint over matte black, heavy armored brawler rigs (bull-bars, riveted plate, ram plows). Tanky, low, wide.
- **Zoomie Syndicate** -- magenta + Neon Cyan `#00F5FF` glow on jet black, low-slung speed rigs (exposed turbines, blade fenders, nitro). Fast, light.
- **Leashbreak Tactix** -- violet + cyan glyphs, hacker tech-vans (antenna arrays, holo dish, EMP emitters). Disables.
- **K9 Circuitry** -- teal + polished chrome and gold, turret-rigs / drone-carriers (rail-cannons, drone bays). Structure-breakers.

---

## 3. THE 48 CHARACTER ICON PROMPTS

Copy a block, PREPEND the Style Bible Line (Section 2), APPEND the Universal Negative, generate 256x256 transparent. Hero cards ($BCARDD, Jagged, Rosco, Crown Foxhound, Stonejaw) use the detailed SEEDANCE_BATTLE_KIT looks.

---

### FACTION 1 -- BONEGUARD CREW (amber + Brick Warm #C1440E, matte-black armored brawler rigs, ram plows)

**0001 -- $BCARDD** *(Dogo Argentino, Mythic, Vanguard, "Crownbreaker")*
```
A pure-white short-coat Dogo Argentino warlord, scarred muscular chest, one cropped ear, intelligent amber eyes, wearing a thin gold-filigree crown fused to a matte-black combat harness with gold knuckle-plates on the paws and a chest sigil. He grips the wheel of THE CROWN RIG: a crowned matte-black armored war-truck (vanta-black #050507 body, hand-laid Crown Gold #D4AF37 trim along every panel seam, a literal welded gold crown over the cab, gold-tipped bull-bar ram plow, twin exhaust stacks, brick-warm #C1440E war-paint scoring). Regal, menacing, the king of the pack. Gold rim light, vanta-black-and-gold color story.
```

**0002 -- Stonejaw** *(Mastiff, Legendary, Vanguard, "Armor Pulse")*
```
A massive fawn English Mastiff, jowled and immovable, battle-scarred muzzle, wearing a riveted iron pauldron-harness and a reinforced jaw-guard with brick-warm #C1440E faction war-paint. He mounts THE STONEWALL: the heaviest brawler rig in the game, a slab-sided matte-black tank-truck with a brick-warm plow blade, rivet-studded armor skirts, and a faint pulsing amber Armor-Pulse aura dome. The wall the lane breaks against.
```

**0003 -- Balboa** *(Boxer, Epic, Striker, "Haymaker")*
```
A fawn-and-white Boxer, alert cropped ears, tight athletic chest, fists-up brawler energy, wearing a brick-warm #C1440E combat vest and gold knuckle-plate gauntlets. Mounted on a compact matte-black brawler rig with a piston-driven battering ram on the nose mid-recoil (haymaker punch). Amber sparks, aggressive forward lean.
```

**0004 -- Iron Rottweiler** *(Rottweiler, Epic, Vanguard, "Overclock Rage")*
```
A black-and-tan Rottweiler, broad heavy jaw, glowing red overclock optic, wearing matte-black plate armor venting red steam from the joints (below-40%-HP rage). Mounted on a battered matte-black armored rig with a brick-warm ram plow and red-hot overclocking exhaust glow. Gold-red rage aura, grinding-forward pose.
```

**0005 -- Granite Saint** *(St. Bernard, Rare, Vanguard, "Bodywall")*
```
A huge brown-and-white St. Bernard, heavy and calm, a small barrel-shaped shield generator at the collar, wearing thick matte-black bodywall armor plating with amber trim. Mounted on a wide, heavy brawler rig with overlapping armor skirts and a blunt ram plow, planting itself to intercept damage. Solid, immovable stance.
```

**0006 -- Grit Bulldog** *(Bulldog, Rare, Striker, "Brawler")*
```
A stocky brindle English Bulldog, low wide stance, undershot jaw bared, wearing a scuffed brick-warm #C1440E harness with a small lifesteal-fang emblem. Mounted on a short, squat matte-black brawler rig with a chewed-up bull-bar ram. Scrappy, aggressive, close-range bite energy.
```

**0007 -- Alloy Akita** *(Akita, Rare, Lancer, "Shock Push")*
```
A curl-tailed Akita with a thick cream-and-grey coat, proud upright posture, wearing matte-black plate with amber accents and a shoulder-mounted shock-cone emitter. Mounted on a mid-weight matte-black rig with a forward concussion-push array on the bull-bar (knockback cone charging). Gold rim light, braced stance.
```

**0008 -- Warden Newfie** *(Newfoundland, Rare, Support, "Fortify")*
```
A massive black Newfoundland, gentle but huge, wearing a matte-black guardian harness with an amber fortify-beacon on the back projecting a soft HP-up aura. Mounted on a broad support rig with a raised armor canopy and amber buff-emitters. Protective, anchored, steady.
```

**0009 -- Rust Cane Corso** *(Cane Corso, Rare, Vanguard, "Grav Pull")*
```
A grey-brindle Cane Corso, cropped ears, lean muscular guard build, wearing matte-black plate with a rust-amber gravity-emitter ring on the chest (taunt pull). Mounted on a low matte-black armored rig with a brick-warm ram plow and a glowing rust-colored grav-coil drawing debris inward. Commanding, magnetic presence.
```

**0010 -- Tank Pug** *(Pug, Common, Support, "Shield Bark")*
```
A small wrinkled fawn Pug, oversized for comedy-tough effect, wearing a chunky oversized matte-black armor shell with amber trim and a tiny shield-bark emitter at the muzzle. Mounted on a tiny but heavily over-armored brawler rig, pint-sized tank energy. Endearing, plucky, well-armored.
```

**0011 -- Copper Chow** *(Chow, Common, Striker, "Bitechain")*
```
A copper-red Chow Chow, thick mane ruff, blue-black tongue, wearing a matte-black harness with copper-amber chain-link bite emitters that ramp brighter per hit. Mounted on a compact matte-black brawler rig with a copper-toned ram. Fluffy but fierce, ramping-aggression pose.
```

**0012 -- Brick Bullmastiff** *(Bullmastiff, Common, Vanguard, "Stonehide")*
```
A fawn Bullmastiff with a dark mask, blocky powerful frame, wearing rough matte-black stonehide plate armor with brick-warm #C1440E texture like masonry. Mounted on a basic heavy brawler rig with a simple ram plow and stone-textured armor skirts. Sturdy, no-frills, grounded.
```

---

### FACTION 2 -- ZOOMIE SYNDICATE (magenta + Neon Cyan #00F5FF, low-slung jet-black speed rigs, nitro/blade fenders)

**0013 -- Jagged** *(Doberman, Mythic, Assassin, "Shadow Fang")*
```
A lean black-and-rust Doberman, clipped ears, a glowing cyan optic-implant over one eye, exposed sprinter sinew, wearing a carbon-fiber speed harness with Neon Cyan #00F5FF glow lines on jet-black and magenta accents. He pilots THE SHADOW FANG: a low-slung blade-thin interceptor rig with exposed turbine intakes venting cyan heat-haze, two retractable energy-fangs on the nose, phase-shimmer cloaking panels. Built to dash and teleport-strike. Cyan rim light, predatory forward crouch.
```

**0014 -- Razor Vizsla** *(Vizsla, Epic, Lancer, "Pierce Rush")*
```
A sleek rust-golden Vizsla, athletic and tapered, glowing cyan-magenta optic, wearing a thin carbon speed harness with cyan glow piping. Mounted on a needle-nosed cyan lancer rig with a forward line-piercing energy spear charging on the hood. Aerodynamic, lunging-forward pose, magenta trail.
```

**0015 -- Aero Malinois** *(Malinois, Epic, Striker, "Twin Strike")*
```
A fawn Belgian Malinois with a black mask, taut working-dog build, mid-motion, glowing cyan optic, wearing a light cyan-trimmed speed harness on jet black. Mounted on a low cyan speed rig with twin nitro-strike emitters flashing two rapid cyan impacts off the front. Kinetic, double-tap motion blur.
```

**0016 -- Pixel Greyhound** *(Greyhound, Rare, Skirmisher, "Dash Loop")*
```
A slender brindle Greyhound, deep chest, tucked waist, mid-sprint freeze-frame, glowing cyan optic-strip, wearing a feather-light cyan-magenta racing harness on jet black. Mounted on the lightest, thinnest skeletal speed rig with glowing cyan dash-loop trails curling behind the wheels. Pure velocity, low aerodynamic crouch.
```

**0017 -- Circuit Shiba** *(Shiba Inu, Rare, Striker, "Blink Bite")*
```
A red-coated Shiba Inu, curled tail, smug fox-like face, glowing cyan optic, wearing a compact cyan-trimmed harness on jet black with blink-teleport glyphs. Mounted on a small low cyan speed rig flickering with a short-teleport shimmer at the nose. Cocky, quick, blink-strike energy.
```

**0018 -- Flash Saluki** *(Saluki, Rare, Skirmisher, "Sidecut")*
```
A graceful feathered Saluki, long elegant lines, glowing cyan optic, wearing a sleek cyan-magenta racing harness on jet black. Mounted on a thin cyan speed rig caught mid lane-swap drift, sideways slide with cyan tire arcs. Elegant, evasive, lateral-cut pose.
```

**0019 -- Bolt Corgi** *(Corgi, Rare, Spawner, "Spark Pups")*
```
A tri-color Pembroke Corgi, big ears, short legs, stubby and charged, glowing cyan optic, wearing a cyan-trimmed harness on jet black with a spark-pup spawn-pod on the back. Mounted on a compact cyan speed rig with a rear hatch releasing three tiny crackling cyan spark-pup drones. Energetic, electric, spawner pose.
```

**0020 -- Glitch Basenji** *(Basenji, Rare, Hacker, "Signal Scramble")*
```
A red-and-white Basenji, alert wrinkled brow, curled tail, glowing magenta-cyan optic, wearing a hacker harness with glitching cyan signal-scramble emitters on jet black. Mounted on a slim cyan rig projecting fractured magenta glitch-static and a silence-pulse. Sharp, jamming, scramble energy.
```

**0021 -- Neon Whippet** *(Whippet, Common, Skirmisher, "Slipstream")*
```
A slim blue-fawn Whippet, ultra-lean, mid-stride blur, glowing cyan optic-strip, wearing a minimal cyan racing harness on jet black. Mounted on a bare-bones thin cyan speed rig with slipstream wind-lines flowing straight through it (ignores slows). Featherweight, streaking-fast pose.
```

**0022 -- Turbo Jack** *(Jack Russell, Common, Striker, "Burst Bite")*
```
A scrappy white-and-tan Jack Russell Terrier, wiry and hyper, glowing magenta optic, wearing a small cyan-magenta harness on jet black. Mounted on a tiny turbocharged cyan speed rig with an oversized rear turbo venting a burst flare (crit on first hit). Manic, explosive, coiled-to-spring pose.
```

**0023 -- Drift Sheltie** *(Sheltie, Common, Support, "Tag Boost")*
```
A sable Shetland Sheepdog, full collie coat, lively, glowing cyan optic, wearing a cyan-trimmed support harness on jet black with a tag-boost speed-emitter. Mounted on a light cyan rig mid power-slide laying down a cyan speed-buff trail for allies. Agile, supportive, drifting pose.
```

**0024 -- Byte Beagle** *(Beagle, Common, Blaster, "Tracer Round")*
```
A tri-color Beagle, long ears, nose-down focus, glowing cyan optic, wearing a backline gunner harness on jet black with a shoulder tracer-cannon. Mounted on a light cyan rig with a long-range cyan tracer barrel firing a shield-piercing round. Ranged, focused, gunner-backline pose.
```

---

### FACTION 3 -- LEASHBREAK TACTIX (violet + cyan glyphs, matte hacker tech-vans, antenna/holo-dish/EMP)

**0025 -- Rosco** *(Australian Cattle Dog, Mythic, Controller, "Leashbreak")*
```
A blue-merle Australian Cattle Dog, alert pricked ears, speckled grey-and-tan coat, a tactical visor projecting a cyan HUD across his eyes, wearing a back-mounted antenna rig and a glyph-projector collar with violet accents and fingerless grip-wraps on the forepaws. He pilots THE JAMMER: an antenna-bristled matte tech-van with a rotating holographic dish on the roof, cyan EMP emitter arms, antenna spines, and violet glyph projectors firing a leash-cut pulse that kills a tower's lights. Signal-warfare command presence.
```

**0026 -- Synth Collie** *(Border Collie, Epic, Hacker, "Hack Jam")*
```
A black-and-white Border Collie, intense herding stare, wearing a cyan HUD visor and a violet hacker harness. Mounted on a matte tech-van projecting a cyan hack-grid from a roof emitter (freezes enemy tower fire). Antenna spines, violet glyph haze, laser-focused pose.
```

**0027 -- Noir Setter** *(Setter, Epic, Controller, "Blackout")*
```
A black Gordon Setter with tan points, long silky feathering, wearing a cyan visor and a dark violet tech harness. Mounted on a matte blackout tech-van emitting a spreading darkness pulse from a roof array (blinds ranged enemies). Shadowy violet haze, stealthy controller pose.
```

**0028 -- Pulse Border Collie** *(Border Collie, Epic, Support, "Barrier Ring")*
```
A red-merle Border Collie, sharp focused eyes, wearing a cyan HUD visor and a violet support harness with a barrier-ring generator on the back. Mounted on a matte tech-van projecting an expanding cyan AoE shield-ring from a roof dish. Antenna spines, protective stance.
```

**0029 -- Holo Husky** *(Husky, Rare, Support, "Heal Beacon")*
```
A grey-and-white Siberian Husky, piercing ice-blue eyes, wearing a cyan visor and a violet medic harness with a holographic heal-beacon emitter. Mounted on a matte tech-van projecting a soft cyan AoE heal aura from a roof dish. Antenna spines, calm supportive pose.
```

**0030 -- Chill Samoyed** *(Samoyed, Rare, Support, "Frost Bark")*
```
A fluffy white Samoyed, signature smile, frost-dusted ruff, wearing a cyan visor and a violet-and-ice harness with a frost-bark cryo-emitter. Mounted on a matte tech-van venting a cyan-white frost AoE slow from front emitters. Cool, crystalline haze, friendly-but-icy pose.
```

**0031 -- Prism Poodle** *(Poodle, Rare, Controller, "Shatter")*
```
A groomed Standard Poodle, refined topknot, wearing a cyan visor and a violet-prism tech harness. Mounted on a matte tech-van with a prismatic shatter-emitter on the roof firing a faceted cyan-violet beam that breaks enemy shields. Sharp, elegant, prismatic light refraction.
```

**0032 -- Signal Pointer** *(Pointer, Rare, Lancer, "Tag Shot")*
```
A liver-and-white English Pointer, frozen on-point stance, one paw raised, wearing a cyan visor and a violet recon harness. Mounted on a matte tech-van with a forward tag-shot targeting lance that reveals stealth (a violet tracking dart charging). Precise, pointing, recon-lancer pose.
```

**0033 -- Ghost Spaniel** *(Spaniel, Rare, Skirmisher, "Phase")*
```
A semi-transparent phasing Cocker Spaniel, long wavy ears, wearing a cyan visor and a violet phase harness, body flickering with brief-invuln shimmer. Mounted on a slim matte tech-van with phase-cloak panels half-faded out. Ethereal, ghostly, mid-phase pose.
```

**0034 -- Echo Dalmatian** *(Dalmatian, Common, Controller, "Echo Howl")*
```
A spotted Dalmatian, sleek and alert, wearing a cyan visor and a violet sonic harness. Mounted on a matte tech-van with concentric cyan echo-howl sound rings rippling out from a roof speaker-array (area slow). Rhythmic, resonant, controller pose.
```

**0035 -- Static Sheba Inu** *(Shiba Inu, Common, Hacker, "Ping")*
```
A cream-coated Shiba Inu, fox-like grin, crackling with static, wearing a cyan visor and a small violet hacker harness with static-ping emitters. Mounted on a small matte tech-van firing a sharp cyan ping-silence burst. Compact, zappy, mischievous hacker pose.
```

**0036 -- Vibe Shih Tzu** *(Shih Tzu, Common, Support, "Soothe")*
```
A small long-haired Shih Tzu, top-knot, soft expression, wearing a cyan visor and a gentle violet support harness with a soothe-emitter. Mounted on a tiny matte tech-van projecting a warm cyan-violet soothing heal glow. Cozy, calm, comforting little support pose.
```

---

### FACTION 4 -- K9 CIRCUITRY (teal + polished chrome and gold, turret-rigs / drone-carriers, rail-cannons/drone bays)

**0037 -- Crown Foxhound** *(Foxhound, Mythic, Assassin, "Royal Hunt")*
```
A regal tri-color American Foxhound, tall and lean, a slim gold circlet between the ears, a polished-chrome cyber-spine running down the back, a gold-and-teal optic. He pilots THE RAILHOUND: a chrome-plated turret-rig with a long gold-tipped rail-cannon spine, drone-bay flanks, hunter-green targeting lasers, polished chrome and Crown Gold #D4AF37 plating with teal accents. The structure-breaker, charging a gold rail-shot. Noble, lethal, hunter pose.
```

**0038 -- Circuit Retriever** *(Retriever, Epic, Support, "Drone Swarm")*
```
A golden Retriever, warm friendly face, wearing a chrome-and-teal carrier harness, a drone-control backpack glowing teal. Mounted on a chrome carrier rig with open flank bays launching a swarm of small teal drones. Helpful, bright, drone-commander pose.
```

**0039 -- Nova Shepherd** *(German Shepherd, Epic, Structure, "Overclock")*
```
A black-and-tan German Shepherd, alert ears, commanding stance, wearing chrome-plated turret armor with teal and gold trim. Mounted on a stationary chrome turret-rig with a rail-cannon overclocking into a burst of gold rapid-fire (turret muzzle glow). Authoritative, fixed-emplacement pose.
```

**0040 -- Laser Beagle** *(Beagle, Rare, Structure, "Overheat")*
```
A tri-color Beagle, ears back in focus, wearing a chrome turret harness with teal heat-vents. Mounted on a stationary chrome turret-rig with a long-range laser barrel glowing teal-to-red as it overheats (ramping damage). Locked-down emplacement, beam-charging pose.
```

**0041 -- Volt Corgi** *(Corgi, Rare, Spawner, "Spark Pups")*
```
A red-and-white Pembroke Corgi, big ears, charged with teal voltage, wearing a chrome-and-teal spawner harness with a drone-pod on the back. Mounted on a chrome carrier rig releasing three crackling teal spark-pup drones from a rear bay. Electric, peppy, spawner pose.
```

**0042 -- Grid Schnauzer** *(Schnauzer, Rare, Structure, "Grid Lock")*
```
A salt-and-pepper Schnauzer, bushy eyebrows and beard, wearing chrome turret armor with teal grid-emitters. Mounted on a stationary chrome turret-rig projecting a teal grid-lock field on the ground (slows enemies). Stern, fixed, grid-control pose.
```

**0043 -- Chrome Airedale** *(Airedale, Rare, Lancer, "Arc Shot")*
```
An Airedale Terrier, black saddle and tan, wiry beard, wearing chrome lancer armor with teal arc-emitters. Mounted on a chrome rig with a forward arc-cannon firing a chaining teal lightning bolt (chain damage). Sharp, kinetic, arc-lancer pose.
```

**0044 -- Beacon Basset** *(Basset, Rare, Support, "Beacon")*
```
A tri-color Basset Hound, long droopy ears, low to the ground, wearing a chrome-and-teal support harness with a tall reveal-beacon mast. Mounted on a low chrome rig projecting a teal scanning beacon-cone that reveals stealth. Mellow, watchful, recon-support pose.
```

**0045 -- Neon Dachshund** *(Dachshund, Common, Spawner, "Tunnel Drones")*
```
A long low Dachshund, smooth red coat, wearing a chrome-and-teal tunneler harness with a drone-burrow pack. Mounted on a low chrome carrier rig with a front tunnel-port releasing small teal burrowing drones. Quirky, low-slung, tunneler-spawner pose.
```

**0046 -- Flux Pomeranian** *(Pomeranian, Common, Support, "Battery")*
```
A fluffy orange Pomeranian, tiny and bright, wearing a chrome-and-teal battery harness with glowing power-cell pods. Mounted on a tiny chrome rig channeling a teal battery-boost beam into a nearby turret. Cute, sparky, energizer-support pose.
```

**0047 -- Rail Terrier** *(Terrier, Common, Blaster, "Rail Shot")*
```
A wiry Rat Terrier, sharp ears, intense, wearing a chrome-and-teal gunner harness. Mounted on a light chrome rig with a shoulder-mounted rail-spike cannon firing a teal anti-structure rail shot (bonus vs structures). Compact, hard-hitting, blaster pose.
```

**0048 -- Pixel Pug** *(Pug, Common, Spawner, "Mini Pup")*
```
A small fawn Pug, wrinkled face, wearing a chrome-and-teal mini-spawner harness with a single drone-pod. Mounted on a tiny chrome rig releasing one small teal mini-pup drone from a side hatch. Endearing, low-cost, starter-spawner pose.
```

---

## 4. CARD-FACE NOTE (optional larger batch)

The same 48 descriptions above work as **card-face portrait art** -- just change the framing in the Style Bible Line from "Small square mobile game unit icon ... readable at 60px" to: `Portrait card art, 2:3 vertical, subject fills 70% of frame, cinematic background implied (faction-colored cyberpunk lane bokeh), full PBR detail, dramatic key+fill+rim, art bleeds to edge.` Generate at ~512x768, PNG. Hero cards (0001, 0002, 0013, 0025, 0037) can instead use their 3-4s Seedance clips from SEEDANCE_BATTLE_KIT.md as the NFT `animation_url` (card-detail screen only, never on the board). Keep the same locked seed/style so faces match their icons.

---

## 5. ARENA / MAP PROMPTS

The board is a portrait Clash-style battlefield: TWO vertical lanes, a central divider/river with TWO side bridges, 3 towers per side (2 princess "Pack Guard" + 1 king "Alpha Den"). The engine is 18 wide x 30 tall tiles, bridges at the left-third and right-third, river across the middle. Render the map as a top-down / slight-angle background; the engine draws lanes, towers, and units on top, so keep tower pads and bridge zones readable and uncluttered.

**Shared map framing (prepend to each variant):**
```
Top-down slight-angle Clash-Royale-style battle board, vertical portrait orientation, two clear vertical combat lanes separated by a central divider with two side bridges crossing it, three tower pads per side (two forward princess pads + one rear king/Alpha-Den pad), gold #D4AF37 faction paint marking the tower pads and lane edges, hyper-real PBR environment (Uncharted 4 city fidelity), cinematic lighting, readable uncluttered lanes for gameplay, vanta-black #050507 deep shadow. No characters, no units, no UI, no text.
```

**MAP A -- Neon-Night Downtown** *(default)*
```
A wet cyberpunk downtown street at neon-night, two lanes carved between glowing storefronts and skyscraper bases, a neon-lit canal as the central divider with two metal side bridges, cyan #00F5FF and magenta neon signage reflecting in the wet asphalt, gold #D4AF37 tower pads glowing, volumetric fog at the far intersection, Midnight Deep #0D0D1A shadow. Premium, electric, night-war mood.
```

**MAP B -- Golden-Hour Industrial**
```
An industrial warehouse-district yard at golden hour, two lanes between corrugated-steel buildings and shipping containers, a dry concrete channel as the central divider with two steel-grate side bridges, warm amber low-sun rim light and long shadows on cracked asphalt, brick-warm #C1440E rust tones, gold #D4AF37 tower pads, dust motes in god-rays. Cinematic, gritty, daytime-war mood.
```

**MAP C -- Rain-Slick Docks**
```
A neon harbor dock at night in the rain, two lanes along wet planked piers, dark water as the central divider with two rope-and-steel side bridges, teal #00F5FF and gold reflections rippling on the rain-slick boards, cargo cranes silhouetted, gold #D4AF37 tower pads, heavy rain streaks and puddle reflections, volumetric mist. Moody, reflective, storm-war mood.
```

---

## 6. DELIVERY SPEC (drop assets in clean)

**Unit icons**
- Format: transparent PNG, exactly **256x256**.
- Name: `<cardNumber>_<slug>.png` where `cardNumber` matches `cards.json` (zero-padded 4-digit) and `slug` is the lowercased name with spaces/dots -> underscores. Examples:
  - `0001_bcardd.png`, `0002_stonejaw.png`, `0013_jagged.png`, `0025_rosco.png`, `0037_crown_foxhound.png`, `0004_iron_rottweiler.png`, `0035_static_shiba_inu.png`.
- Location: `ecosystem/game/assets/units/`

**Card faces (optional)**
- Format: PNG (or .mp4 Seedance clip for the 5 heroes), ~512x768 (2:3).
- Name: `<cardNumber>_<slug>_card.png` (or `_card.mp4`).
- Location: `ecosystem/game/assets/cards/`

**Arena / maps**
- Format: PNG, portrait, **~540x900** (the board's portrait ratio; 18:30 = 3:5).
- Name: `arena_a_neon_night.png`, `arena_b_golden_industrial.png`, `arena_c_rain_docks.png`.
- Location: `ecosystem/game/assets/arena/`

**Wiring (after upload):** once the files exist at those paths, the game's `drawUnit` is switched from the placeholder role-silhouette + rig-glyph to `ctx.drawImage()` of `units/<cardNumber>_<slug>.png` (looked up by the unit's `cardNumber`), and the board renderer loads the chosen `arena/*.png` as the match background under the lanes/towers/units. Drop-in swap, no stat or layout changes.

---

*Art Prompt Pack v1.0 -- 2026-06-03. 48 icon prompts (4 factions x 12) + 5 hero looks from the Seedance kit + 3 arena variants. Prepend the Style Bible Line and append the Universal Negative to every icon prompt. Route every generation through the ART_BIBLE 3-stage review gate before it enters the repo. No AI slop.*
