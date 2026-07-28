# HERO PLATES -- 6 PLAYABLE COMMANDERS
## Action portraits (hero-select art) + mesh plates (Tripo input)

Source of truth: `game/handlers_data.js` (breed, accent, special, passive, capstone),
`AK_BLOCK_CHRONICLES_BIBLE.md` ($BCARDD canon), `HANDLER_CLASSES_LIVE.md` (roles).
Every breed, aura color and ability below is copied from those files, not invented.

---

## READ THIS FIRST -- THESE ARE TWO DIFFERENT ASSETS

You asked for action portraits AND meshes. They cannot be the same image.

| | ACTION PORTRAIT | MESH PLATE |
|---|---|---|
| Purpose | hero-select screen, card art, marketing | feed `image_to_3d` in Tripo |
| Pose | dynamic, mid-ability, foreshortening | neutral A-pose, arms/forelegs clear of body |
| Light | cinematic, rim light, haze, practical sources | flat even overcast, no cast shadows |
| Lock | `STYLE_LOCK.md` | MESH HERO LOCK (below) |
| Frame | any crop that reads well | full body, head to paws, headroom, 3:4 |

**An action pose will not mesh.** Limbs crossing the torso weld together in
photogrammetry, foreshortening destroys proportion, and a cape or muzzle flash
becomes permanent geometry. Cinematic haze and film grain bake in as surface
noise -- the same reason the building plates had to drop the cinematic lock.

**Portraits already exist** at `game/assets/handlers/*.jpg` (1080x1440, all six).
So the mesh plates are the real gap. Generate those first if credits are tight.

---

## MESH HERO LOCK
### Prepend to every MESH plate. Do NOT use `STYLE_LOCK.md` on these.

```
Full-body character reference photograph, vertical 3:4, single anthropomorphic dog
character centered and complete in frame, three-quarter front view, neutral upright
A-pose with forelimbs held clear of the torso and hind legs shoulder width apart,
entire figure visible from ears to paws with clear headroom, even diffuse overcast
studio light, no cast shadows, sharp focus edge to edge, deep depth of field,
photoreal, high material detail, neutral flat grey background
```

### MESH NEGATIVE (append to every mesh plate)

```
no motion blur, no film grain, no volumetric haze, no lens flare, no shallow depth
of field, no dramatic shadow, no crossed limbs, no props held across the body,
no cropping, no tilt, no fisheye, no humans, no text overlays, no watermarks
```

For `multi_image_to_3d` generate 3 angles per hero -- front, three-quarter, side --
same pose, same light. Triples the credit cost, roughly triples mesh quality.

---

# 1. THE MENDER
**Breed:** St. Bernard / Medic · **Aura:** `#7FE3A0` med-green · **Glyph:** rescue helmet
**Special:** Field Kennel -- healing totem, 3.5 tile radius, 8% maxHp/sec, 35s
**Passive:** Pack Scent -- all friendlies regen 2% maxHp/sec
**Capstone:** Revive Protocol -- 30% chance to revive an ally who dies in radius
**Energy:** the one who stays. Immovable calm in a firefight, slow deliberate hands,
the only dog on the block who runs toward the screaming.

**ACTION PORTRAIT**
```
Massive St. Bernard field medic dog standing braced over a fallen packmate in a
rain-slick neon alley, one huge paw planted, deploying a glowing green field-kennel
totem, med-green volumetric light washing up his chest and jaw, weathered rescue
harness and battered medical panniers, snow-matted heavy coat soaked dark at the
shoulders, steam rising off him, heavy lidded eyes fixed and unafraid, low hero
angle, dolly push-in
```

**MESH PLATE**
```
Massive anthropomorphic St. Bernard medic, heavy double coat in rust and white,
worn leather rescue harness with med-green cross panels, medical saddle panniers,
thick neck, broad blunt muzzle, heavy brow, calm steady expression
```

---

# 2. THE TRACKER
**Breed:** Bloodhound · **Aura:** `#E2B23A` amber · **Glyph:** hound
**Special:** Scent Probe -- reveal enemies in 6 tiles, marked take +25% damage 8s
**Passive:** Keen Senses -- 0.5s vision preview on enemy deploys, kills charge faster
**Capstone:** Tag -- marked enemies cannot stealth
**Energy:** patience as a weapon. Never hurries, never loses the thread, already
knows where you slept last night.

**ACTION PORTRAIT**
```
Lean Bloodhound tracker crouched low on wet asphalt mid-stride, muzzle down to the
ground, long ears dragging, amber scent-probe rings pulsing outward from his nose
across the street, glowing amber target reticles painting the dark behind him,
deep facial folds and heavy drooping jowls, hooded amber eyes lifted toward camera,
sodium vapor streetlight overhead, handheld, tracking shot
```

**MESH PLATE**
```
Anthropomorphic Bloodhound tracker, deep red-brown coat, extremely long pendulous
ears, heavily wrinkled brow and loose facial folds, drooping jowls, lean rangy
frame, worn amber-tagged tracking collar, simple strapped field vest, alert
downward-tilted head
```

---

# 3. THE SHADOW
**Breed:** Basenji · **Aura:** `#9B8CFF` violet · **Glyph:** new moon
**Special:** Slipstream -- ally gains 25% speed and untargetable stealth 1.5s
**Passive:** Swift Paw -- all friendlies move 8% faster
**Capstone:** Assassin's Edge -- stealth-exit attack deals +50% crit
**Energy:** the barkless one. Basenjis do not bark -- lean into that. Arrives
without sound, leaves before the room knows, never once announces himself.

**ACTION PORTRAIT**
```
Sleek Basenji assassin caught mid-slipstream sprint along a rain-wet rooftop edge,
body stretched flat in full extension, violet motion trails and cloaking shimmer
peeling off his flanks as he half-dissolves, tightly curled tail, sharply pricked
erect ears, wrinkled forehead, short glossy chestnut coat, almond eyes lit violet,
silent open mouth, low angle against neon skyline, tracking shot
```

**MESH PLATE**
```
Anthropomorphic Basenji, short glossy chestnut and white coat, small athletic
lightweight frame, sharply erect pointed ears, tightly curled tail over the hip,
distinctive wrinkled forehead, fitted dark violet-trimmed bodysuit wrap, minimal
gear, poised alert stance
```

---

# 4. THE RIGGER
**Breed:** Doberman, Engineer · **Aura:** `#D45A2C` burnt orange · **Glyph:** wrench
**Special:** Drop Rig -- deploy Gun Nest, Tesla Coil or Flak Turret
**Passive:** Structure Durability -- structures last 40% longer
**Capstone:** Forge Protocol -- unlocks a 4th rig, the Suppressor
**Energy:** builds under fire. Grease to the elbow, welding mask pushed up,
solves every problem by bolting something to it.

**ACTION PORTRAIT**
```
Doberman engineer slamming a turret drop-pod into cracked asphalt, bracing it
one-handed as it unfolds, orange sparks and tesla arcs spitting off the coil,
welding mask shoved up on his forehead, tool harness and cable spools slung across
his chest, sleek black and tan coat streaked with grease and soot, cropped ears,
long tapered muzzle, teeth bared in effort, orange rig-glow underlighting him,
handheld, low angle
```

**MESH PLATE**
```
Anthropomorphic Doberman engineer, sleek short black and tan coat, cropped erect
ears, long tapered muzzle, lean muscular athletic build, heavy canvas tool harness
with burnt-orange webbing, cable spools and wrenches at the hip, welding mask
pushed up onto the forehead, work-scarred forearms
```

---

# 5. THE BRUISER
**Breed:** Pit Bull / Mastiff, tank archetype · **Aura:** `#C0392B` red · **Glyph:** fist
**Special:** War Cry -- nearby allies +20% damage, +18% maxHP shield, 3.5s
**Passive:** Squad Toughness -- units under your command take 8% less damage
**Capstone:** Last Stand -- War Cry shield adds damage reduction on blocked hits
**Energy:** the wall the block hides behind. Takes the hit so nobody else has to,
and gets louder the worse it goes.

**ACTION PORTRAIT**
```
Enormous Pit Bull Mastiff roaring a war cry mid-street, head thrown back, jaws wide,
red shockwave rally rings blasting outward and lifting debris and rain off the
asphalt, colossal slabbed shoulders and barrel chest, thick corded neck, broad
blocky head, heavy undershot jaw, scarred short brindle coat, chain-and-plate
shoulder armor, red aura firelight on wet fur, low hero angle, dolly push-in
```

**MESH PLATE**
```
Anthropomorphic Pit Bull Mastiff tank, enormous heavily muscled build, colossal
sloping shoulders and barrel chest, thick corded neck, broad blocky head with heavy
undershot jaw, cropped ears, short scarred brindle coat, riveted chain-and-plate
shoulder armor with deep red trim, heavy studded collar, planted grounded stance
```

---

# 6. THE DEALER ($BCARDD)
**Breed:** Dogo Argentino, Card #0001, the $BCARDD mascot · **Aura:** `#D4AF37` gold
**Special:** House Edge -- flip a card for gold, pups, heal or gamble
**Passive:** Small Blessing -- +0.5% bonus gold per 30s elapsed
**Capstone:** $BCARDD Blessing -- Coin Explosion, 300 AOE in 2 tiles
**Energy:** swagger as a load-bearing wall. The house always wins, and he is
the house. One of only four Mythics that will ever exist.

**LOOK IS LOCKED CANON -- DO NOT REINTERPRET.** White-coat Dogo Argentino,
cropped ears, gold crown, flag aviator shades, $-B gold chain, gold cigar.
Bible: *"took the alley throne bare-fanged and never looked back."*

**ACTION PORTRAIT**
```
White-coat Dogo Argentino kingpin mid-card-flip, gold $BCARDD coin-card spinning
lit in the air above his paw, gold jackpot light and coin burst exploding around
him, gold crown set between cropped ears, flag-pattern aviator shades, heavy gold
$-B chain, gold cigar clamped in a fanged grin, pure white muscled coat, casino
neon and falling coins, low hero angle, dolly push-in
```

**MESH PLATE**
```
Anthropomorphic Dogo Argentino, pure white short muscled coat, cropped erect ears,
broad powerful head and deep chest, gold crown, flag-pattern aviator sunglasses,
heavy gold dollar-B pendant chain, gold cigar in mouth, tailored dark vest,
confident upright stance
```

---

## GENERATION ORDER (credit balance 231.52, verify before spending)

1. **6 mesh plates** at `seedream_v4_5` (~1 cr each) -- ~6 credits. This is the gap.
2. Cheap test pass first with `z_image` (0.15 cr) to check pose and framing -- ~1 credit.
3. Only if you want new hero-select art: 6 action portraits (~6 credits). The
   existing six at `game/assets/handlers/*.jpg` already fill this slot.
4. `multi_image_to_3d` at 3 angles per hero triples both cost and mesh quality.

## INSTALL PATH FOR FINISHED MESHES
`game/assets/models/hero_<id>.glb`, ids from `handlers_data.js`:
`handler_mender`, `tracker`, `handler_shadow`, `the-rigger`, `bruiser_handler`, `the-dealer`.

Tripo exports normalise to roughly unit size. This world is pixel-scaled and the
hero is 60 units tall, so a raw GLB lands about 1 unit and is invisible -- the exact
bug that made `bcardd.glb` render 0.3 pixels. Normalise by bounding box on load.
