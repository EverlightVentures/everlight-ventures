# ALLEY KINGZ -- ART BIBLE v1.0
*Authored: 2026-03-01 | Chief Operator: Claude / Everlight Hive Mind*
*Status: APPROVED FOR AI GENERATION + OUTSOURCE BRIEF*

---

## VISUAL IDENTITY: ONE SENTENCE

> **Alley Kingz is hyper-real urban power -- cinematic street culture rendered with Clash Royale clarity and Uncharted 4 texture fidelity, on a mobile-first canvas.**

---

## 1. CORE AESTHETIC: STYLIZED HYPER-REALISM

Not photorealism. Not cartoons. The sweet spot:
- **High detail, high contrast, readable at 60px**
- **PBR materials** -- leather feels worn, gold catches light, concrete shows age
- **Exaggerated proportions** where needed for readability (characters slightly heroic in scale)
- **Culturally authentic** -- this is Black urban America. Locs, fades, fitted caps, Forces, Timbs. Not generic fantasy.

Reference tier targets:
- Character quality: Clash Royale + Street Fighter 6 character renders
- Environment quality: Uncharted 4 urban levels + The Last of Us city blocks
- Card quality: Hearthstone Legendary + NBA TopShot moment frames

---

## 2. COLOR PALETTE (5 PRIMARY COLORS -- LOCKED)

| Name | Hex | Use |
|------|-----|-----|
| **Crown Gold** | `#D4AF37` | Hero accents, Legendary borders, crowns, chains |
| **Midnight Deep** | `#0D0D1A` | Backgrounds, card base, shadow fill |
| **Neon Cyan** | `#00F5FF` | Skill FX, rare glow, UI highlights |
| **Brick Warm** | `#C1440E` | Urban environment tones, Epic borders, danger |
| **Asphalt Grey** | `#4A4A55` | Secondary backgrounds, Common card borders, streets |

Supporting (accent only, never dominant):
- Blood Orange `#FF4500` -- damage indicators, loss states
- Ivory Cream `#F5F0E8` -- skin highlight, paper textures

**Rule:** Every asset must contain at least 2 of the 5 primary colors. No pastel washes. No rainbow palettes.

---

## 3. LIGHTING MOOD

**Primary mood: Golden Hour Urban + Neon Night**

- Golden hour = warm amber rim light from low-angle sun, long shadows on asphalt
- Neon night = deep blues/purples in shadow, cyan/magenta neon from signage cutting through
- Never flat lighting. Every character has a key light, fill, and rim
- Volumetric effects: fog at intersections, god rays through warehouse skylights, mist from grates
- Indoor scenes: Edison bulb warmth + industrial fluorescent cool contrast

**Prohibited:** Flat cel shading, neutral grey ambient only, pure white backgrounds on characters

---

## 4. CHARACTER VISUAL RULES

### Body Proportions
- Heroic scale: heads slightly larger than realistic for card readability
- Builds match faction: Territory Kings = broad/imposing, Street Chemists = lean/precise, Grid Runners = athletic/dynamic

### Skin Rendering
- Subsurface scattering on all skin -- no plastic-flat shading
- Melanin range: full spectrum represented authentically
- Sweat/weathering where character archetype demands (fighters, laborers) -- skin shows story

### Clothing
- PBR materials only: leather creases, denim threads visible, fabric drape physics-appropriate
- Streetwear authenticity: no generic "fantasy armor" reboots. Faction colors expressed through real garment choices
- Accessories: chains, watches, fitted caps, glasses -- all modeled as separate geometry with specular highlights

### Face Rules
- Eyes: always lit, iris detail visible, slight specular catch light
- Expression: decisive / confident / intense -- not neutral or smiling
- No ambiguous ages: characters must read clearly as adult

### Card Silhouette Rule
- At 200x300px thumbnail, the character must be instantly readable by silhouette alone
- Pose: dynamic 3/4 angle, weight in one foot, gesture telegraphing role

---

## 5. CARD DESIGN SYSTEM

### Rarity Tiers
| Rarity | Border | Glow | Frame Material | Pull Animation |
|--------|--------|------|----------------|----------------|
| Common | Asphalt brushed steel | None | Matte metal | Slide in |
| Rare | Blue chrome | Subtle pulse | Polished chrome | Flip + glow |
| Epic | Brick/orange flame | Ember sparks | Hammered copper | Flip + particle burst |
| Legendary | Crown Gold holographic | Crown glow + radiant pulse | Gold foil emboss | Cinematic reveal + shockwave |

### Card Layout (locked)
- Art bleeds to edge -- no white border
- Name plate: frosted glass overlay, bottom 20% of card
- Power stats: top-right corner, bold numerals
- Faction icon: top-left corner, embossed
- Flavor text: 1 line max, italic, 9pt equivalent, inside name plate

### Card Art Composition
- Subject fills 70% of card vertically
- Action or environment implied in background
- Depth: foreground element, mid subject, background blur (bokeh or painterly)

---

## 6. AREAS / MAP VISUAL RULES

### Perspective
- Isometric 45-degree top-down for gameplay maps
- Cinematic straight-on for cutscene/loading art

### Environmental Storytelling
- Every area has: 1 faction mark (graffiti, banner, car color), 1 hazard element, 1 ambient life element (people, animals, vehicles)
- Time of day established by shadow angle -- never ambiguous
- Weather: either fully dry (golden hour clarity) or fully wet (puddle reflections, rain streaks). No ambiguous grey.

### Area LOD Budget
- Hero area art: 4K texture, high-poly geometry
- In-game tile: max 2K texture, max 50K poly per scene, ASTC/ETC2 compressed

---

## 7. SHOP VISUAL RULES

- Shop = underground luxury. Think exclusive sneaker drop meets underground card room.
- Featured item: always rendered as 3D rotating holographic projection
- Limited time offers: red countdown timer, slightly desaturated non-featured items (focus pulls to deal)
- Shopkeeper NPC: consistent character, changes outfit seasonally
- UI panels: frosted glass with Crown Gold trim, never solid opaque boxes

---

## 8. MOBILE PERFORMANCE CONSTRAINTS (NON-NEGOTIABLE)

| Asset Type | Max Texture | Max Poly | Compression |
|------------|-------------|----------|-------------|
| Character (card) | 2K | 45K | ASTC 6x6 |
| Character (in-game) | 1K | 20K | ETC2 |
| Background / Map tile | 2K | 50K/scene | ASTC 6x6 |
| Shop UI | 1K sprites | N/A | PNG-8 where possible |
| Particle FX | 512px atlas | N/A | No alpha bleeding |

**Test device floor:** Snapdragon 665 / Mali-G52 / 4GB RAM. If it does not hit 60FPS here, it does not ship.

---

## 9. WHAT THIS IS NOT

- Not a fantasy game -- no dragons, no swords, no magic in the traditional sense
- Not 90s sprite work -- no flat fill, no dithering, no pixel art nostalgia
- Not generic hip-hop stereotype -- it is elevated, intelligent, cinematic
- Not AI slop -- every AI draft goes through Art Review Gate before acceptance

---

## 10. VALIDATION GATE

All assets must pass this 3-stage check before being added to the asset repo:

1. **AI Draft** -- generated from approved Prompt Bible prompts
2. **Art Review** -- Chief Operator or designated lead reviews for style consistency, proportion, palette compliance
3. **Performance Check** -- compressed, benchmarked on test device, added to content_pack.json manifest

*Any asset failing stage 2 or 3 returns to the Gemini prompt pipeline for regeneration, not acceptance.*

---

*Art Bible v1.0 -- Changes require Chief Operator sign-off. Feed this document into every AI generation session and every outsource brief.*
