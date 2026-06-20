# ALLEY KINGZ -- DEEP-DIVE SYNTHESIS (THE GLUE, operator 2026-06-20)
> The unifying design that ties every system together: 3D depth, video, mission/faction KARMA, unified economy, base-building, Solana. Reconciled against the LIVE build (the 8 AK_SYSTEMS waves + worldmap + the edge fns). Companion to AK_MASTER_GAME_DESIGN_SYNTHESIS.md (the 14-game fusion) + AK_2D_3D_CONCEPT.md (3-mode) + AK_SYSTEMS_DESIGN.md.
> RECONCILIATION KEY -- most of this is ALREADY BUILT as waves; the GLUE is (a) connecting them + (b) the net-new layers. Per-part status below.

## PART 1 -- 3D DEPTH ("too flat") -- NET-NEW (UI/menus only)
Decision: NOT Three.js/Babylon (would break the Canvas2D stack). Use **CSS 3D transforms + "extruded photo"** (perspective + preserve-3d + translateZ side/bottom faces) = the Brawl-Stars 2.5D look, ~0KB, GPU, mobile-fine.
SCOPE NOTE: this is a CSS/DOM technique -> applies to the DOM MENUS (district-select cards, shop card grid, collection, keeper portraits), NOT the Canvas2D walkable hub (which gets its depth from the district backgrounds + parallax). Build as a reusable `.extruded-photo` CSS class + a tilt-on-pointer JS shim, applied to the shop/menu card surfaces.

## PART 2 -- VIDEO / MP4 -- PARTLY LIVE
Decision: **cinematic loops** (3-5s, muted, playsInline, low-opacity, mix-blend-mode), a CinematicLoop manager capping ~3 concurrent (budget + priority eviction). 
STATUS: LIVE -- menu_bg.mp4 is on the hub loadscreen + game.html lobby (shipped 2026-06-20). NEXT: a `game/systems/loops.js` manager for per-building/per-district ambient loops (neon flicker, rain, smoke) + the deploy "glitch" loop + NPC idle loops. Generate 720p/3s/H.264/~500KB via Leonardo/Runway from existing art.

## PART 3 -- MISSIONS + FACTION KARMA -- missions LIVE, KARMA is NET-NEW (the headline glue)
Decision: dual-track -- Combat Reputation (fighting) + **district SOCIAL KARMA** (helping). Per-district karma, 7 tiers (Stranger -> New Face -> Known -> Trusted -> Respected -> Revered -> Legend) gating missions/shop-discounts/NPC-dialog/building-access/perks. FRIENDLY ENCOUNTERS: a d100 table modified by karma (low karma = mostly hostile strays; high karma = friendly NPCs/resources/special). Friendly NPCs: Lost Pup, Injured Stray, Merchant Caravan, Faction Recruiter, Mysterious Stranger (story chain). Karma converts to crew Reputation at high tiers.
STATUS: missions wave LIVE (FIXER deliveries via ak-quests). KARMA = a new `game/systems/karma.js` module: per-district karma store (falsy-default profile field `karma:{}`), the tier table, karma-gated content, + extend `encounters.js` so a roamer roll can be FRIENDLY (not just the hostile stray). Districts map to the 4 factions (Crowned/Rusted/Hologhosts/Unbound) + neutral Central Plaza.

## PART 4 -- UNIFIED ECONOMY -- currencies LIVE, the WEB/SINKS is the glue
Decision (Sunflower-Land model): every currency has a SOURCE + a SINK + a CONVERT path; no dead-ends. Gold/Gems/Scrap/Keys/Bones (+ Wood/Stone/Metal materials + Reputation + Karma + Consumables). The synergy loop: ONE action touches 3+ currencies. BURN per currency (anti-inflation): Gold 60% (upgrades/repairs), Scrap 70% (forge can fail), Keys 100% (consumed), Bones 100% (skill nodes), Wood/Stone 50% (raids destroy), Karma 0% (prestige resets).
HARD: Gems NEVER buy power (time/cosmetic/convenience only); Bones soulbound (never tradable). STATUS: all currencies exist across the waves; the GLUE = formalize the source->sink->convert web + the burn rates + wire the cross-wave conversions (e.g., karma->rep at high tier, materials->scrap at Chop Shop). A balancing/wiring pass, not new currencies.

## PART 5 -- TOWN HALL + BASE BUILDING -- Town Hall LIVE, the GRID is World-Map Sprint 2
Decision: 9-tile personal island (-> 16 @ TH7, -> 25 @ TH10), buildings snap to grid, walls/barricades on the perimeter, raids hit your ACTUAL layout (CoC). TOWN_HALL_GATES table caps card-level + crew-size + builders + grid-size per TH level. Barricades: wood(200hp)/stone(500)/metal(1200)/electric(800,+DPS). 12 building types with W/S/M costs. To upgrade TH: all production maxed for the tier + avg card level >= TH*2 + gold + time.
STATUS: Town Hall meta-gate LIVE (card-level cap + upgrade). The 9-tile GRID + snap-placement + walls = World-Map Sprint 2 (extends worldmap.js: the zoom-out view becomes the editable base; AK_COLLISION.validPlacement already exists for the placement rule).

## PART 6 -- SOLANA / $KINGZ -- DEFERRED (per the synthesis's own rule)
Decision: **launch the game first, crypto second.** $KINGZ (1B fixed supply): 40% game-rewards / **9% FOUNDER (operator)** / 11% team+advisors (4yr vest) / 15% ecosystem / 15% treasury / 7% liquidity (locked) / 3% airdrop. Utility = governance/staking/cosmetic-marketplace/optional-tournament-entry/pass-discount.
**FOUNDER STAKE (operator law 2026-06-20):** a PERMANENT **9% = 90M $KINGZ** reserved for the operator as the cash-out stake (liquid at TGE or short-vest; at $1/coin = ~$90M). Carved from the synthesis's 20% team pool -> 9% founder + 11% team. This 9% is RESERVED in every tokenomics revision, non-negotiable.
**$BCARDD <-> $KINGZ OFFICIAL TIE (operator ask 2026-06-20):** dual-token model -- **$BCARDD = the OFFICIAL MEME / MASCOT / CULTURE coin of the $KINGZ ecosystem** ($BCARDD = card #0001 the Dealer, the faceless-founder meme that drives virality); $KINGZ = the game utility/governance token. The tie = (1) BRAND + lore (officially "the meme of Alley Kingz / $KINGZ" -- the mascot/face of the whole ecosystem), (2) COSMETIC cross-benefit ($BCARDD holders get $KINGZ-ecosystem cosmetic perks + airdrop allocation -- cosmetic ONLY), (3) optional later $BCARDD/$KINGZ DEX liquidity pair. LEGAL GUARDRAIL: keep them STRUCTURALLY SEPARATE -- no utility-for-token, no profit-dependency between them -- so pairing doesn't STACK securities risk; $BCARDD stays the geo-gated cosmetic/meme coin (our crypto gate), $KINGZ the deferred game token. Theo GC sign-off BEFORE any on-chain tie or DEX pair. HARD (anti-Axie): never required for core play, never buys power, never breed-for-profit, always a sink, always transparent. 5 phases: soft-launch (no crypto) -> wallet-connect -> airdrop (earned, not bought) -> marketplace+staking -> governance. Stack: @solana/web3.js + Anchor; Phantom/Solflare/Backpack; Metaplex NFTs; Helius indexing; Arweave storage. LEGAL: utility-token-not-security, no US without KYC/geoblock, Theo GC sign-off BEFORE launch.
STATUS: DEFERRED until the game proves out (consistent w/ our existing crypto-gate: $BCARDD/ALK cosmetic+geo-gated only). Keep all crypto code stubbed.

## PART 7 -- BUILD SEQUENCE (12-week from the synthesis, reconciled to our LIVE state)
The synthesis's wk1-12 (3D-depth+video / karma+missions / unified-economy / town-hall+base / solana-stubs / polish) -- but missions/economy/town-hall/video are ALREADY shipped as waves, so our ACTUAL next sequence (operator order this turn = 1,3,2):
1) OBSTACLE-COLLISION for the 6 remaining districts (extend AK_COLLISION) -- IN PROGRESS.
3) WORLD-MAP SPRINT 2 -- other players' bases (ak-raid snapshots on the map) + base-REARRANGE (drag + validPlacement) + the material economy (wood/stone/metal gather+build).
2) AK_DESIGN_AUDIT fix-list (specs/AK_DESIGN_AUDIT.md).
THEN the synthesis net-new: KARMA module (Part 3), the loops.js video manager (Part 2), the CSS extruded-photo menu treatment (Part 1), the economy-web/burn wiring pass (Part 4). Solana stays deferred (Part 6).

## PART 8 -- TECH STACK (confirmed)
Canvas2D + CSS-3D (front) / HTML5 muted video loops / Node + Postgres + Supabase (back) / Solana + Anchor (deferred) / Phantom+Solflare+Backpack / Metaplex / Helius / Arweave.

## THE GLUE, IN ONE LINE
Hub-walk (depth via backgrounds + CSS-3D menus + ambient video loops) -> KARMA-gated friendly+hostile encounters + missions -> a unified-economy web where every action ripples 3+ currencies -> spent on a CoC base you arrange + defend -> all soft/cosmetic now, $KINGZ as the deferred cherry. Every wave we shipped is a node in this web; KARMA + the economy-web are the connective tissue.
