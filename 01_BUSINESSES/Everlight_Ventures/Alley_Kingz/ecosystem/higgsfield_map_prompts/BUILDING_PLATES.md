# BUILDING PLATES -- PORTRAIT, MESH-READY
## 19 full-building portrait photos built to survive image-to-3D conversion

These are DIFFERENT from the in-district building shots in `01_..09_`. Those are
cinematic beauty shots for video. THESE are clean architectural plates whose only
job is to feed `image_to_3d` / `multi_image_to_3d` and come out as a usable mesh.

---

## CRITICAL: DO NOT USE `STYLE_LOCK.md` ON THESE

The cinematic style lock actively RUINS 3D meshing. Volumetric haze, film grain,
heavy shadow, and shallow depth of field all bake into the geometry as noise or
get read as surface detail that is not there. The photogrammetry pass needs the
opposite of a cinematic look.

### MESH STYLE PREFIX (prepend to every building plate)

```
Full-frame architectural portrait photograph, vertical 3:4, single isolated
building centered and complete in frame, three-quarter front view showing two
facades, entire structure visible from ground to roofline with clear headroom,
even diffuse overcast daylight, no harsh shadows, sharp focus edge to edge, deep
depth of field, photoreal, high detail, neutral flat background
```

### MESH NEGATIVE PROMPT (append to every building plate)

```
no people, no vehicles, no foreground objects, no cropping, no tilt, no fisheye,
no motion blur, no lens flare, no film grain, no fog, no haze, no bokeh, no
dramatic lighting, no night scene, no neon glow, no text, no watermark, no
cartoon, no illustration
```

**Why:** `three-quarter front view showing two facades` is the single most important
line. A dead-on front view gives the 3D model no depth information and produces a
flat slab. Two visible faces is what lets it infer volume.

### RECOMMENDED SETTINGS

- Aspect: **3:4 portrait** (the buildings are taller than wide; portrait wastes less frame)
- Model: `seedream_v4_5` (1 credit) for the pass, `nano_banana_pro` (2) if detail is short
- Generate **3 angles per building** if you plan to use `multi_image_to_3d` -- swap
  `three-quarter front view showing two facades` for `three-quarter rear view` and
  `direct side elevation`. Triples cost, roughly triples mesh quality.

---

## ARCHITECTURAL LOGIC (why each building looks the way it does)

Style is driven by TWO axes, per your note: district location and building function.

| District | Architectural vernacular | Why |
|---|---|---|
| THE LOT | American mixed-era municipal, patched and added-onto | neutral ground, oldest part of the city, nobody rebuilt it |
| DOWNTOWN | converted commercial brick, retrofitted storefronts | commerce grew into existing bones, fast and cheap |
| NEON HEIGHTS | high-modern glass and chrome, deliberate | the only district with money to build new |
| THE YARDS | salvage architecture, containers and scrap | built from what the city threw away |
| FACTORY ROW | heavy Victorian industrial, iron and brick | purpose-built for production, never updated |
| THE STRIP | googie casino vernacular, signage-first | architecture as advertisement |
| THE DOCKS | port utility with clinical tech inserts | old port shells with new tech surgically added |

---

# THE LOT (neutral / gold / uptown)

## TOWN HALL (`ARENA`) -- seat of the block
```
A heavy brutalist civic arena building, 1960s municipal concrete construction,
board-formed concrete with visible wood grain texture, deep-set recessed window
slots, a broad shallow flight of concrete entry steps spanning the full facade,
massive scarred double doors in oxidized bronze, a cantilevered slab canopy over
the entrance, faded painted signage ghosted on the concrete, patched repairs in
mismatched grey, low squat proportions built to intimidate, four stories, flat roof
with exposed mechanical housing
```

## TROPHY HALL (`TROPHY`) -- trophies / profile
```
A small neoclassical civic hall, weathered limestone ashlar, four fluted columns
supporting a plain pediment, tall narrow arched windows with divided lights, a
raised stone plinth base with worn steps, copper roof gone green with age, modest
two-story scale, symmetrical and formal, soot staining in the carved recesses,
dignified and slightly undersized, the architecture of a town that once had money
```

## THE KENNEL (`KENNEL`) -- handlers, kept by Mama Bones
```
A converted American craftsman bungalow, deep covered front porch with tapered
square columns on stone piers, low-pitched gabled roof with wide eaves and exposed
rafter tails, weathered clapboard siding painted a faded green, brick chimney on
the side elevation, a sagging screen door, mismatched added-on rear extension in
different siding, single story with a dormer, domestic and worn and lived-in
```

## INFIRMARY (`INFIRMARY`) -- rest and recover
```
A small mid-century clinic building, single story, clean horizontal lines,
buff-colored brick with a continuous band of steel-framed windows, a flat roof with
a thin projecting fascia, a simple recessed entry under a cantilevered concrete
canopy, glass block panel beside the door, utilitarian and calm, institutional but
not cold, minor water staining below the window band
```

---

# DOWNTOWN (Unbound / magenta / midtown)

## THE DROP (`DROP`) -- the SHOP
```
A converted brick loading-dock building turned retail storefront, ground floor
opened up into a full-width glass shopfront with a heavy steel lintel above,
original red brick upper floor with segmental-arched windows, a raised concrete
loading dock lip still present along the base, a folded steel awning, roll-down
security shutter housing above the glass, three stories, painted-over ghost signage
on the brick, commercial retrofit over industrial bones
```

## THE GARAGE (`GARAGE`) -- deck builder
```
A brick automotive workshop building, two large corrugated steel roll-up doors
across the front, a steel-sash industrial window band above them, painted brick in
a faded utilitarian color, a flat parapet roof with a simple stepped cornice, a
small pedestrian door to one side, exposed conduit and a wall-mounted extractor
fan, two stories, functional and sturdy, oil-stained concrete apron at the base
```

---

# NEON HEIGHTS (Crowned / teal / midtown)

## THE WARDROBE (`WARD`) -- Drip cosmetics
```
A flagship luxury boutique building, full-height glass curtain wall in a slim
anodized frame, polished chrome mullions, a double-height ground floor with a
frameless glass entry, an upper floor clad in fluted metal panels, a cantilevered
canopy of brushed steel, immaculate stone paving at the base, four stories, sharp
geometry with no visible fasteners, expensive and severe, nothing weathered
```

## THE ARCHIVE (`ARCH`) -- the Codex
```
A brutalist stone monolith library, near-windowless facade in massive precast
panels with a deep vertical rib pattern, one narrow full-height slot window, a
recessed shadowed entrance at the base reached by a low stone ramp, heavy
cantilevered upper mass overhanging the entry, five stories, monumental and
defensive, deliberately at odds with the glass district around it, knowledge as
fortress
```

---

# THE YARDS (Rusted / rust / docks)

## CREW YARD (`CLAN`) -- crews / chat
```
A compound built from stacked shipping containers, three containers high in a
staggered arrangement, welded steel catwalks and external stair runs connecting
levels, cut window openings with salvaged frames, corrugated container ribbing in
mismatched faded reds and blues and greens, rope bridge to an adjacent stack,
improvised corrugated roof canopy over the top level, rust bleeding down every
seam, ingenious and unpermitted
```

## PASS HOUSE (`PASS`) -- Alley Pass
```
A narrow brick rowhouse, single bay wide and three stories tall, dark soot-stained
brick, tall narrow sash windows in a strict vertical stack, a stepped Dutch gable
parapet at the roofline, a single recessed doorway with a worn stone threshold,
iron tie plates visible on the facade, a downpipe running the full height, cramped
and vertical, squeezed between missing neighbors
```

## THE FIXER (`FIXER`) -- Hit List / jobs
```
A lean-to shack of tar paper and salvaged corrugated steel, timber frame visible
where the covering has torn, a mismatched salvaged door, one small window covered
by a steel grate, a stovepipe chimney through the roof at an angle, the whole
structure leaning slightly and propped by a diagonal timber brace, single story,
low and mean, built to be overlooked
```

---

# FACTORY ROW (Rusted / forge orange / docks)

## GEM MINE (`GEM`) -- production: gems
```
A mine headframe pithead building, tall riveted steel lattice headframe tower
rising above a squat brick engine house, large sheave wheels mounted at the top of
the tower, a corrugated steel ore chute running down at an angle, industrial
staircases bolted to the exterior, small grimy windows in the brick base, heavy
riveted plate detailing throughout, five stories to the wheel, purposeful and
skeletal
```

## GOLD MINT (`MINT`) -- production: gold
```
A fortress-like iron vault building, massive rusticated stone base course, heavy
riveted iron plate cladding on the upper mass, tiny barred slit windows placed high
and sparse, a single enormous vault door recessed in a stone surround, square
corner guard turrets with crenellated tops, a flat roof with a heavy projecting
cornice, three stories, squat and impenetrable, built to be unassailable
```

## CARD FORGE (`FORGE`) -- production: cards
```
A Victorian industrial factory with a sawtooth north-light roof, long brick facade
with regular cast-iron-framed windows in segmental arches, a tall round brick
chimney stack at one end, a projecting gabled entry bay with a hoist beam and pulley
above the loading door, corbelled brick cornice detailing, external steel fire
stair, two tall stories, soot-blackened and purpose-built
```

---

# THE STRIP (Unbound / magenta / docks)

## THE STREET (`STREET`) -- street mode
```
A low commercial strip building in googie roadside style, an angled cantilevered
roof plane projecting far past the facade, full-width plate glass storefront below,
a tall freestanding pylon sign structure integrated at one end with empty sign
panels, a boomerang-shaped canopy support, terrazzo base, mismatched later infill
between original bays, single story with a tall parapet, architecture designed to
be seen from a moving vehicle
```

## THE ARCADE (`ARCADE`) -- mini-games
```
A converted warehouse amusement arcade, plain concrete block box structure
completely dominated by an enormous blank marquee sign frame across the entire
facade, chase-light bulb sockets ringing the marquee, a deep recessed entry vestibule
with angled glass ticket booth, glass block side panels, no windows on the main
volume, two stories of blank wall behind the signage, the sign is the building
```

---

# THE DOCKS (Hologhosts / violet / docks)

## RESEARCH LAB (`LAB`) -- production: skill pts
```
A converted port warehouse with a clinical laboratory insert, weathered corrugated
steel shed structure with a shallow gabled roof and rusted flashing, one bay
surgically replaced with a sealed white composite panel volume and a strip of
mirrored glazing, external ducting and filtration housings bolted along the flank,
a sealed airlock entry with a steel frame, contrast between rotting shell and
sterile insert, two stories, wrong in a quiet way
```

## THE GENERATOR (`GEN`) -- production: power
```
A compact industrial power plant building, reinforced concrete mass wrapped in a
dense exterior lattice of cooling pipework and insulated ducting, two tapered
concrete cooling stacks rising from the roof, a bank of finned heat exchangers on
the flank, external cable trays and heavy conduit runs, a small reinforced control
room bay with narrow windows, warning placards on the plant, four stories, humming
and overbuilt
```

---

# UNPLACED

## THE FENCE -- trade and launder goods
```
A narrow corner pawnshop and trade building, ground floor storefront with heavy
steel security grilles over every opening, dark brick upper floors with painted-over
windows, an angled corner entrance door cut across the building corner, a projecting
blade sign bracket with the sign removed, a roll-shutter housing above the grille,
two stories, closed and watchful, a place that does not want to be looked at
```

**Note:** THE FENCE exists in the Bible's building list but has NO entry in `ZONES`.
It has no district and no coordinates. Plate provided since you asked for all
buildings, but it cannot be placed in game until someone assigns it a district.
Best fit on theme is THE YARDS or THE STRIP.
