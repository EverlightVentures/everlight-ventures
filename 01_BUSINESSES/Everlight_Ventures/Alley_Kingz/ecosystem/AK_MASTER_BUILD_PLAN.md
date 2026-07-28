# Alley Kingz -- MASTER BUILD PLAN (consolidated 2026-06-22)
*Three vision waves, one plan. The north star: AK is a HERO-team builder (Ni no Kuni) + an ECONOMY (Clash of Clans) + an ARMY/defense game (Dark War) + a card COLLECTION that is a Pokedex + MISSIONS (Pokemon) + minigames (Monopoly) -- a real city-state where your 11-card deck IS the town's people, and everything you do on the world map feeds one shared rank that also drives the tower battle. Consistency law: Town Hall gates everything; ONE economy (AK_ECON); gems = cosmetic/skip/pay-recovery ONLY; engine.js FROZEN; 60fps hub; AK Supabase = mfghdobptredxxhbjwyz; deploy via e5 ship.sh.*

## SHIPPED + VERIFIED (2026-06-22)
- Town Hall facade (was a black box) + TH-level sync (building/HUD/gates = one number).
- Dispatched-builder harvest ("send a dog, walk away") + timer bars on mining/build/crops.
- Social layer flipped ON in the hub: "you were raided" live ping + CREW + sign-in while walking.
- CITY DEPTH P1 (faction-city + district identity + specialty +20% + market tax), P2 (faction-flavored service interiors + map banners), P4 (public transit chip + TH-discounted fare).
- DECK-AS-PEOPLE render: the dispatched builder is now a REAL owned deck card (its portrait art) and its LEVEL drives work speed.

## THE STAKES LOOP -- the spine that ties world <-> tower <-> economy (from the synergy audit)
Today there are TWO disconnected rank systems and ZERO stakes: raid resolve() early-returns on a loss, settleRaidServer only posts won:true, and p.trophies is never written. So you can be raided in your sleep and lose nothing. The fix = ONE shared rank (p.trophies) + card death + TH downgrade as the stake + the infirmary as the rebuild:
1. **Shared rank (p.trophies):** +trophies on tower/encounter WIN (game.html grantMatchRewards), -trophies on raid LOSS. One ladder for world + tower. [M, client]
2. **Raid consequence branch (SERVER):** ak-raid resolve() on a real-base loss -> re-check shield -> card-level debit (a max card drops a level) + Town Hall downgrade + trophy loss, computed service-side, applied via negative ak_grants on next load. [L, server -- mfghdobptredxxhbjwyz, the highest-risk piece]
3. **Shield enforcement INSIDE resolve()** (not just targeting): a shielded base rejects the raid. [S, server]
4. **Recovery economy:** dead card -> INFIRMARY (heal-over-time, free, TH-gated slots) OR re-recruit (scrap/produce) OR faction-heal (karma Trusted+) OR gem instant (server-only pay path). New p.infirmary shape + systems/infirmary.js. [L]
5. **Raid-report aftermath overlay** (what you lost while offline). [M]

## CITY DEPTH -- remaining
- **P3 district control + treasury** (SERVER): claim a district by raiding it -> owner sets its tax -> revenue to the crew treasury.
- **P5 district-laws UI + mayor/tax-collector NPCs.**
- **P6 sensory:** locked-district bg art (overlook, undercity), districtsfx.js, faction signage, per-district particles.

## WAVE 3 -- hero / pokedex / types / tap-upgrade / custom-art (being audited: workflow wf_82e5e6a1)
- **HERO / main character:** first-start pick (or random Epic..Mythic) a HERO dog = the walking avatar; it shapes faction + skill-point focus + which random battles/missions you hit. Build hero + team around it.
- **POKEDEX:** every card a dex entry (caught/uncaught, collection %, how-to-catch); tie the leash/capture encounter into it. (Assess codex.js.)
- **TYPE strengths/weaknesses:** a Pokemon-style element per card + a type-effectiveness multiplier layered (via data/modes, NOT frozen engine.js) into tower battle + world map + street fights.
- **TAP-TO-UPGRADE buildings:** tap a building (don't enter) -> Upgrade popup with time + resources + builders required.
- **STREET FIGHT:** a SEPARATE Rare/Mythic-gated TOUGH mode (keep the leash/capture); tower battle stays Town-Hall-only.
- **CUSTOM ART EVERYWHERE:** no generic emojis on major menus/populated surfaces -> a catalog of every surface + a prompt-ready description, sent to the image/video/music AI.

## RECOMMENDED BUILD ORDER (highest leverage first)
1. **Shared trophy rank** (client, ties world+tower -- the cheapest piece of the stakes spine).
2. **Tap-to-upgrade buildings** (self-contained, immediately useful, complements the build system).
3. **Type system** (data layer on cards + a modes-level multiplier -- big gameplay depth, no engine edits).
4. **Hero / first-start pick** (onboarding + avatar-as-card).
5. **Raid consequence + shield enforcement + infirmary** (the SERVER stakes loop -- a deliberate migration on mfghdobptredxxhbjwyz; biggest, do with fresh context).
6. **Pokedex** (collection screen + capture wiring).
7. **Custom-art generation pass** (art_factory + districtmusic from the manifest) + transit ride visual + P3/P5/P6.

## ASSET MANIFEST (to generate -- art_factory / Leonardo / districtmusic; from the audits)
- **Graphics:** transit vehicle (bus/cab/metro 2.5D) + transit line-map; infirmary keeper (Doc Wattson) + recruiter portraits; raid-report card-damage/crack overlay frames; shield crest (shielded vs vulnerable); division/Masters rank emblems (Bronze..Master); street-fight "tat in the leash" capture-victory frame; locked-district bgs (overlook, undercity); faction signage (4); + the wave-3 custom-art catalog (every emoji surface -> real art).
- **Music:** infirmary theme (warm/clinical), transit ride stinger, street-fight tension theme, + per-faction district beds.
- **SFX:** card-death/level-drop sting, TH-downgrade rumble, trophy-pip + rank-up flourish, infirmary heal-tick, re-recruit whistle, gem-skip shimmer, transit engine/doors, shield-expiring alarm, capture chime.

## RISK NOTES
- SERVER-AUTH is the #1 risk: card death / TH downgrade / trophy loss / gem-skip must live ONLY in ak-raid / a new ak-recovery edge fn (service role) on mfghdobptredxxhbjwyz, computed from the DEFENDER's record (never trusted from the attacker client).
- engine.js FROZEN: the type system layers via card data + a modes-level multiplier, never engine edits.
- 60fps hub: all new UIs lazy-DOM (mirror #thpanel); no per-frame heavy work.
- Save shape: every new profile field (trophies write path, infirmary, hero, dex, types) added falsy-default in ensureShape -> zero-state byte-identical.

## WAVE-3 AUDIT CONFIRMED (wf_82e5e6a1, 2026-06-22) + art pipeline live
Audit verified the gaps: codex.js is a READ-ONLY wiki (no p.dex caught-tracking); the 106 unit cards have NO type field (only the 5 spells do); avatar is hardcoded "STRAY" (no heroCard); only the Town Hall has tap-to-upgrade (producers force a dwell-enter); skill points (p.sp) exist but have NO spender. Surgical roadmap (engine.js stays FROZEN -> type effects layer via canon data + a modes/encounters multiplier, NOT engine edits):
- TYPE taxonomy as data (canon.js TYPE_FROM_FACTION + 5x5 effectiveness) [S] -> type multiplier applied at the modes/encounters layer [M].
- p.dex Pokedex state in ensureShape + pokedex.js render (caught/uncaught, collection %, how-to-catch) [M/L]; codex.js stays the wiki.
- onboarding.js first-start HERO pick (3-5 random Epic..Mythic) -> profile.heroCard -> herostate.js maps the avatar + HUD to the hero [M/S].
- skill-point spender (economy.spendSkillPoint -> p.skills[card] stat patches, applied at the stat-reader, not engine) [M].
- tap-vs-dwell split on building pointerup -> #upg-panel (next level + cost + time + builders) [M]; timed builder-gated producer upgrades [L].
- ART MANIFEST: see AK_ART_MANIFEST.md (62 prompt-ready definitions + music + video) -- kill generic emojis on every major surface (17 building icons, 9 HUD chip icons, action/type icons, keeper portraits, rank emblems, transit vehicle, raid-report frames).
- ART PIPELINE LIVE: art_factory.py + CF/Leonardo keys confirmed; a queue drain (--limit 28, incl. 3 validation building icons icon_arena/gem/forge) kicked off in background 2026-06-22 -> review style before wiring (no generic art stays).

## KILLSTREAK / KILL-SCALING DEEP-DIVE (wf_df954588, 2026-06-22) -- BIG FINDING
**The kill-scaling power-up the operator described ALREADY EXISTS in the TOWER battle engine.** engine.js has per-unit killStreak (line 1239) + a 5-tier EVO_TIERS evolution (base -> ... -> "DOG GOD" @8 kills, +40% dmg/hp, +15% atkSpd), applyEvolution() mutating dmg/maxHp/atkSpd (captures base stats so death resets cleanly), crown text + golden particles + screen shake + sfx('evo_up') on tier-up, clamped under DMG_CAP=1.8. So the tower piece is BUILT -- and engine-frozen-safe to enhance (the host reads u.evoTier off global.AK.game each frame; no engine edit needed for cosmetic overlays).
GAPS (build these): 
1. RAID kill-scaling -- DONE this session (modes.js: kstreak/ktier per unit, +22% dmg/+12% hp/tier + kill-heal, 3-tier aura green/gold/magenta + ★ pips, resets on respawn). Encounters/gulag still need the same pattern.
2. Cosmetic FX overlay (host-side, game.html post-update hook reading u.evoTier) -> make the tower evolution BIGGER/cooler. No engine edit.
3. Cosmetic effects/skins SHOP (Brawl-Stars-style) -- extend DRIP_CATALOG (shop.js ~1479) with type:'effect' kill-effect/particle/skin cosmetics. The Drop + Locker already exist + are coin/parity-safe.
**PARITY VERDICT (HARD -- tell the operator):** the "buyable STAT-BUFF / mythic attributes" (CoD DMZ) idea = PAY-TO-WIN and violates the gem gate (gems cosmetic-only). DO NOT sell stat power. Sell VISUAL effects/skins only (gem-safe cosmetic); kill-scaling STATS stay 100% EARNED via kills. If "mythic attributes" are added at all, they must be EARNED/grind, never bought. (Renderer can read a separate u.cosmeticEvotier for flashier visuals at the same power -- cosmetic, parity-safe.)
- ASSET MANIFEST add: per-tier kill-effect FX (rim-glow colors, particle trails, crown sprites, palette shifts) + per-tier sfx variants -> AK_ART_MANIFEST.md.

## THE GLUE -- "CROWN CLIMB" cohesion spine + de-emojify (wf_aa3fedd4, 2026-06-25)
CORE FINDING: the art is ALREADY SHIPPED but never WIRED -- the HUD renders emoji while assets/icons/chip_*.png + assets/ui/cur_*.jpg + assets/portraits/keeper_*.png + struct_*.png + interiors all exist. "Why did we pay for graphics" is literally true on the top bar. AND the game reads as a pile of systems because there's no narrative state machine connecting them.
THE SPINE -- window.AKStory (NEW systems/story.js, client-deterministic, gated off profile flags, NO engine/server): you arrive a STRAY -> climb to KING. 7 stages: (1) Meet the Fixer (delivery -> unlock Hit List), (2) Pick Your Faction (recruiter; Crest_*.jpg exist), (3) Prove Yourself (karma->Trusted unlocks crew), (4) Crew Wars (raid/guard turf), (5) Seasonal Supremacy (the 6-wk seasons.js chapter = that faction's ERA, +1.5x on its districts -> Supremacy Tournament), (6) Challenge the King (boss tower battle at season-final), (7) reign/prestige. Cards-are-your-people already true (dispatched builders, captured roster). Every system becomes a rung, not a side toy.
ROADMAP (11 phases): 1a WIRE HUD rail->chip_*.png [S~1h]; 1b WIRE production keepers->keeper_*.png [S]; 1c WIRE game.html menu tabs->assets/ui facades + fix the wrong World Map glyph [S]; 2 builder-cap unify (buildersBusy(p) in economy.js consumed by worldverbs+index akOpenUpgrade) [M]; 2b visible builder-dog on upgrade [S]; 3 in-world glyph de-emojify (harvest nodes/structures) [M]; 4 stand up window.AKStory spine [L]; 5 MERGE the two job systems into ONE HIT LIST (missions.js + mission_active.js) [M]; 6 mini-games -> CREW TRAINING that feeds the RPG (capped ct/rewards) [M]; 7 Sunflower MARKETPLACE on ak-trading [M]; 8 district GUARDING (task='guard' builder slot) [L]; 9 CO-OP missions (acceptWithCrew, split rewards) [M]; 10 season integration [M]; 11 remaining glyph cleanup (spells canon.js:3671, karma tiers, NPCs, raid defense) [M].
ART: WIRE-EXISTING (no gen) = HUD->chip_*.png, keepers->keeper_*.png, menu tabs->assets/ui (Deck.jpg/Crew.jpg/...), world-map->Crest_*.jpg, structure palette->struct_*.png, mini-game tokens->real card art (akCardArtRel), marketplace->#tradepanel+ak-trading. GENERATE (CF, match chip_*.png style bible) = harvest node glyphs, 6 season icons, 5 spell icons, 7 karma tier badges, 5 NPC icons, 5 raid-defense icons, arcade keeper_jonah, HUD non-currency chips. RISK: style drift (generate against the chip_*.png reference); a SECOND currency asset set exists (cur_*.jpg vs chip_*.png) -- pick ONE (chip_*.png) to avoid a fork.
NOTE: also flagged -- TWO job systems (missions.js FIXER + mission_active.js recruiter) should MERGE into one Hit List (phase 5).
