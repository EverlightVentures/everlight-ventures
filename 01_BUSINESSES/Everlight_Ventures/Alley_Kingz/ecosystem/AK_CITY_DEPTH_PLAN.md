# Alley Kingz -- CITY DEPTH PLAN
*Synthesized 2026-06-22 from a 5-dimension parallel code audit (workflow ak-city-depth-audit). The operator's vision: each FACTION is a CITY, each district its SUBDIVISION/neighborhood; same store-TYPES faction-flavored; per-neighborhood taxes/rules; municipal governance + public transit; a real city-state feel -- not just a video game. Everything stays consistent with the Town Hall gate / cards / upgrades / mining / gems / ONE economy (AK_ECON). AK Supabase = mfghdobptredxxhbjwyz only.*

## The core gap
The faction map already EXISTS (karma.js: 4 crews own the 8 outer districts, Home Turf neutral) -- but it was invisible and inert. Districts were interchangeable (name + tint only); there was NO per-district economic character, NO governance/ownership, NO transit, NO faction-flavored services, and the locked districts had no art. The whole "city-state" vision hangs off ONE missing foundation: a **district-identity + per-neighborhood-rules model**. Build that, and taxes, faction services, district laws, transit, and NPC flavor all attach to it.

## The faction-cities (from karma.js DISTRICTS -- the canonical map)
- **The Crowned** 👑 (K9 Circuitry, #00E0C0): NEON_HEIGHTS (capital) + THE_OVERLOOK -- elite heights.
- **The Rusted** 🦴 (Boneguard, #C9772E): THE_YARDS + FACTORY_ROW -- scrap/industrial.
- **The Hologhosts** 👻 (Leashbreak, #7B5CFF): THE_DOCKS + THE_UNDERCITY -- tech/phantom.
- **The Unbound** ⚡ (Zoomie, #FF2E88): DOWNTOWN + THE_STRIP -- hungry hustle.
- **Central Plaza** 🏙️ (neutral): HOME_TURF -- tax-free home turf.

## TOP PRIORITY -- BUILT + DEPLOYED 2026-06-22 (P1: Faction-City & District Identity)
The foundation everything else hangs off, made FELT in one slice:
- `window.AK_DISTRICTS` (index.html) -- reads AKKarma faction (ONE source), adds each neighborhood's SPECIALTY resource + market TAX + accent.
- **Identity title-card** on district entry: "FACTORY ROW · 🦴 The Rusted City · METAL district · 6% market tax".
- **District specialty** (worldverbs): mining a neighborhood's signature resource yields +20% (★ banner). Home=wood, Downtown/Strip=produce, Neon Heights=stone, Yards=scrap, Factory Row/Docks=metal.
- **Market tax** (trade panel): cashing materials -> gold on faction turf takes a 6% cut (neutral plaza free); shown in the preview + deducted for real. Soft-currency only; TH/cards/gems untouched.

## ROADMAP -- next (ranked; each ties to the consistency strategy)
- **P2 Faction-flavored services** (M) -- same store TYPES in every neighborhood, faction-skinned name/keeper (THE DROP -> "Royal Exchange" on Crowned turf). Refactor B()/keeperFor to take the district faction. Ties to: existing buildings + FAC facade map.
- **P3 District control + treasury** (L, server) -- a crew CLAIMS a district by raiding its base; owner sets the tax rate; tax routes to the crew treasury. Persist in ak_player_bases/new ak_districts table (Supabase mfghdobptredxxhbjwyz). Ties to: raid system + crews (both already live).
- **P4 Public transit** (M) -- a TRANSIT stop (🚌) in 2-3 hub districts; tap -> fast-travel menu with a gold fare (vs free walking). Higher Town Hall unlocks more lines. Ties to: zone graph + TH gate.
- **P5 District laws + municipal UI** (M) -- a "DISTRICT LAWS" panel (mirrors #mkpanel): controlling crew, tax rate, specialty, a mayor/boss NPC + roaming tax-collector roamer. Ties to: P3 ownership + karma board.
- **P6 Per-district sensory** (M, art+audio) -- see asset manifest. Locked-district bg art, per-district particle tints, environmental SFX layer (districtsfx.js mirroring districtmusic.js), faction signage.

## ASSET MANIFEST (to CREATE for the sensory package)
- **Graphics**: `overlook_bg.png` (Crowned checkpoint -- cold blue/security lights), `undercity_bg.png` (Hologhost underground -- deep blue/rubble/emergency lights); 11 missing building interiors (trophy_hall, drop_shop, garage, wardrobe, archive, crew_yard, pass_house, fixer_den, street_mode + others); per-faction signage/banner art (4 factions); faction-tinted particle sets.
- **Music**: confirm a DISTINCT districtmusic theme per faction-city (4) + the neutral plaza; ambient bed per district mood (elite/industrial/tech/hustle).
- **SFX**: `districtsfx.js` ambient layer -- per-district footsteps (factory metallic / downtown concrete / docks hollow-wood) + ambient loops; building-interior ambient cues (forge clang, mine drill, mint coins).

## RISKS
- **60fps hub**: identity banner + specialty are O(1)/event-driven (safe). Transit/laws UIs must be lazy DOM (mirror #thpanel/#mkpanel), no per-frame work.
- **One economy / crypto gate**: every per-district modifier stays soft-currency + routes through AK_ECON.mutateProfile. Gems NEVER touch tax/yield/loot. Tax shown only where it's actually applied (no display-lies, per the Town Hall fix).
- **Server (P3)**: district ownership must be server-authoritative (anti-cheat) on mfghdobptredxxhbjwyz -- a deliberate migration, not client localStorage.
- **Save shape**: new profile fields (treasury, district control) added as falsy-default in ensureShape -- zero-state byte-identical.
