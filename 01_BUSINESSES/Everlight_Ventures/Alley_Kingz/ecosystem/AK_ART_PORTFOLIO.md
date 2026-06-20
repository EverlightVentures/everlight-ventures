# ALLEY KINGZ -- ART & MAP DESIGN PORTFOLIO (the art bible; 2026-06-19)
> 47 maps | 12 art categories | 340 assets | 89 prompts. Feeds the art factory (Leonardo bulk) + Seedance (premium hero). Companion to ALLEY_KINGZ_TODO.md + AK_MASTER_BLUEPRINT.md.

## STYLE GUIDE (the bible)
Aesthetic: urban-fantasy street art x cyberpunk neon x cartoon strategy. Refs: Clash of Clans (readability), Sunflower Land (charm), Brawl Stars (attitude), Fortnite (cultural relevance).
Palette: Primary = Electric Purple #8B5CF6, Neon Cyan #06B6D4, Hot Pink #EC4899. Secondary = Graffiti Orange #F97316, Toxic Green #22C55E, Street Gold #EAB308. Neutrals = Asphalt #1C1917, Concrete #78716C, Brick #991B1B. Accents = Siren Blue #3B82F6, Fire Red #EF4444, Smoke White #F5F5F4.
3 golden rules: (1) recognizable by SILHOUETTE alone, (2) readable at 64x64 (icons) and 200x200 (chars), (3) everything feels one universe.

## 47 MAPS
TIER 1 -- World maps (3): MAP_01 Core District (2000px, downtown neon alleys, default) | MAP_02 Outskirts (2500px, industrial/scrapyards, MainTower L10) | MAP_03 Neon Abyss (3000px, megacity/sky-bridges, Prestige 2). Main Tower = tallest, pulsing neon crown, visible everywhere (the 10-sec hook).
TIER 2 -- Building interiors (16): Main Tower/Crew HQ, Spell Shop, Deck Lab, Training Grounds, Crew Hall, Marketplace, Bounty Board, Shield Station (Core); Advanced Spell Forge, Deck Evolution, Beast Arena, Black Market (Outskirts); Ascension Temple, Legendary Card Forge, Sky Arena, Creator Hub (Neon Abyss).
TIER 3 -- Mini-game maps (12): Card Clash Arena, Crew War Battlefield (3 lanes), Beast Hunt, Scrap Yard Scramble, Casino Heist, DvD War Zone, Pool Hall, Dart Board, Obstacle Course, Memory Match, Graffiti Tag, Crew Trivia.
TIER 4 -- Clan mission maps (10): Heist, Siege, Rescue, Ritual(boss), Convoy, Defense, Exploration, Rivalry, Gauntlet, Revenge counter-raid.
TIER 5 -- UI/HUD (6): Main HUD overlay, Crew War lane assignment, DvD war map, Card+Gear inventory, Crew Chest opening anim, Push notifications x5.

## 340 ASSETS (12 categories)
Characters 25 (avatars 10/leaders 5/vendors 5/raiders 5) | Cards 50 (common 15/rare 15/epic 12/legendary 8) | Building exteriors 20 | Vehicles/Mounts 15 | Weapons/Gear 30 | VFX 40 | Iconography 60 | Backgrounds 20 | Promotional 15 | NFT/Blockchain 25 (land 10/skins 10/frames 5) | Cinematics 10 | Emotes 30.

## PROMPT TEMPLATES (for the art factory / Seedance)
- MAP: "[RENDER_STYLE] [LOCATION] in [THEME], [KEY_FEATURES], [INTERACTIVE], [ATMOSPHERE], [LIGHTING], cartoon strategy game [MAP_TYPE], [COLORS], [SIZE], game asset, [BG_TYPE], Unity-ready"
- CHARACTER: "Stylized cartoon urban [TYPE], [TRAITS], wearing [CLOTHING], [ACCESSORIES], [POSE], distinct readable silhouette, design sheet front/back/side, cartoon strategy game character, [COLORS], transparent background, game asset, Unity-ready"
- BUILDING: "Isometric 3D [TYPE] exterior, [ARCH STYLE], [SIGNAGE], [DECOR], [DISTINCTIVE], readable silhouette, [DISTRICT] architecture, cartoon strategy game building, [COLORS], transparent background, game asset, Unity-ready"
- CARD: "[RARITY] trading card, [BORDER] border + [FX], [CONCEPT] in [POSE], [SPELL FX], name banner top, stats panel bottom, rarity gem corner, CCG aesthetic, [COLORS], [SIZE], game asset, Unity-ready"
- Example MAP_01: "Isometric 3D urban street scene at night, neon signs electric purple + cyan, graffiti brick walls, wet asphalt reflecting lights, steam from manholes, glowing street vendor carts, cyberpunk alleyways w/ hidden doorways, Clash-of-Clans-but-grittier, vibrant saturated, clean readable silhouettes, 2000x2000, 64x64 grid, transparent bg for objects, Unity-ready."

## PRODUCTION PHASES (route via art_factory.py -> Leonardo bulk; Seedance for hero pieces)
- PHASE 1 (4-6wk, vertical slice): MAP_01 Core District, INT_01 Main Tower interior, UI_01 HUD, 5 player avatars, 15 common cards, 8 core building exteriors, MINI_01 Card Clash, UI_05 Crew Chest anim, 5 core spell FX, MAP_02 Outskirts.
- PHASE 2 (6-8wk, beta): Outskirts buildings 6, rare cards 15, mini-games 6, clan missions 5, UI screens 3.
- PHASE 3 (8-10wk, launch): Neon Abyss, epic+legendary cards 20, remaining mini-games 6, remaining clan missions 5, NFT assets 25, cinematics 10.

## ROUTING (see feedback_art_autoroute_no_generic memory)
Bulk environment/buildings/props/icons/maps -> Leonardo via art_factory.py (--enqueue) or generate_hub_assets.py pattern (cheap, API). Premium hero pieces (Main Tower, key avatars, cinematics, MAP hero shots) -> Seedance (operator, manual). Gritty house style auto-appended. Every new item with art auto-routes (no generic placeholder stays).
