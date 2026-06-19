# ALLEY KINGZ -- GRAND PLATFORM ROADMAP (deep-dive 2026-06-18)
"The GTA of phone games." Card-battler core, walkable-world overlay, cosmetic flywheel, social UGC pull. V1.25 -> V2 -> V3 -> V4.

## 1. THESIS
AK is not a Clash Royale clone -- it's a walkable cyberpunk-dog underworld where the card battle is ONE NODE in a
living city (the way farming is one node in Sunflower Land, shooting one node in Fortnite's social layer). Clash's
ceiling is the match; AK's ceiling is the WORLD AROUND the match -- crews, an arcade, a Drop, a city. Carbon-copying
Clash = a combat loop with no reason to return between matches. Cross-pollinating Sunflower (retention via
destinations) + Gods Unchained (ownership dopamine) + Fortnite (cosmetic/pass flywheel) + Roblox (UGC/social
liveness) = a platform with a daily-return habit + non-pay-to-win monetization + a moat no single-genre competitor
matches. We WIN because the battler is already juiced + fun -- we WRAP it, never rewrite it.

## 2. CROSS-POLLINATION MATRIX
| Source | Mechanic | Maps onto AK | Version |
|---|---|---|---|
| Sunflower | hub + one-tap teleport Map | city-map hub of tappable nodes; Arena node = existing startMatch() | V2 (ships first) |
| Sunflower | zone-gating (locked-but-visible nodes) | gate Arcade behind trophy lvl, Black Market behind crew-join (reuse trophy state) | V2 |
| Sunflower | minigames as iframe PORTALS (JWT in, postMessage score out) | Arcade node -> minigame menu; 1-file canvas apps, credits via ak_grants; never touches combat | V2 |
| Sunflower | factions(4) + faction house + shared Faction Pet (week buff) | re-skin AK's STAGED social layer (crews+chat+donations); crew levels a mascot -> +% gold at grantMatchRewards | V2 |
| Sunflower | Weekly War (crew leaderboard + bonus) | server tally of trophies/wins -> payout via ak_grants (reuses logged results) | V2 |
| Sunflower | two-currency + rewards-mint-on-spend (~75% recycle) + expiring seasonal currency | gold/gems/Bones; seasonal Pass currency WIPES at season end (forces spend) = Gem-Back Flywheel | V2 econ, matures V3 |
| Sunflower | walkable Plaza w/ live bodies (Colyseus presence) | ONE shared scene, dog avatars walk + see real players (AK e5 Social Phase 3 infra) | V2 Tier2 -> V3 |
| Gods Unchained | on-chain card ownership + fee'd P2P marketplace | COSMETICS-ONLY trade (alt-art skins, Drip) + 5-20% studio fee -- capture trade dopamine WITHOUT a FLOWER-style token (sidesteps Howey/gambling) | V2 cosmetic mkt; token decision V3+ |
| Fortnite | Battle Pass + quests + rotating shop + cosmetics | Alley Pass + Hit List + The Drop + Drip (in-match cosmetic = card alt-art swap); already GO'd | V1.25 -> V2 |
| Roblox | UGC + social liveness | portal pattern lets community build minigames; activity ticker + NPC dogs fake liveness cheaply | V2 seed -> V4 UGC |

## 3. PLAN A -- "2.5D NOW" (V2). Doctrine: WRAP-DON'T-REBUILD. Battler/deck/cards/art/sounds stay byte-identical. Keep the battle ONE TAP away always.
- **Phase 0 -- Feel-Proto (1-2 days, DO FIRST):** bare iso hub, dog avatar, tap-to-move, 3 placeholder nodes (Arena/Garage/Clan Yard). Arena calls existing startMatch() (confirms zero engine coupling). GOAL: prove the walk feels good before investing. Judge as a player.
- **Phase 1 -- Static Hub "menu that looks like a world" (Tier 1, ~3-5 days):** styled screen-router city map, tappable nodes + corner teleport. **NO avatar locomotion needed for ~80% of the retention value.** Nodes: Arena(battler), Garage(deck+card cosmetics), The Drop(shop, live on Stripe), Clan Yard(crews), Arcade(locked), Black Market(locked). Reuses trophy state, lobby art, brand CSS. EFFORT: LOW (pure UI over existing screens).
- **Phase 2 -- Crew/Faction Social Overlay (~1 wk):** activate the ALREADY-STAGED social_layer.sql migration (Supabase, RLS forced, writes via edge fns). Clan Yard = roster + chat + shared Faction Pet (donate gold -> level mascot -> week +% gold buff) + Weekly War leaderboard. Cheers/follow/DM. EFFORT: MEDIUM, zero combat change.
- **Phase 3 -- Arcade Portals (~1 wk, parallelizable):** Arcade node -> NPC -> minigame menu; each minigame an iframe/route, AK mints session token -> postMessage score/claimPrize -> credit via ak_grants. Launch set: Chop Shop Whack, Alley Dash (runner), Heist Memory. Daily-claim cap. Art via art factory. Bonus: any portal can ship standalone (Telegram/web) as top-of-funnel. EFFORT: MEDIUM, fully decoupled.
- **Phase 4 -- Seasonal Economy + Cosmetic Marketplace (~1 wk):** Alley Pass pays a seasonal currency that WIPES at season end; cosmetic-only P2P marketplace (alt-art/Drip) w/ studio fee = the only P2P monetization. NO on-chain token in V2. EFFORT: MEDIUM, ledger/data only.
- **Phase 5 -- Walkable Plaza (Tier 2, optional, ~2 wks):** ONE shared scene, real players (Colyseus on e5 -- Social Phase 3, additive). Seed w/ NPC dogs + activity ticker. EFFORT: HIGH -- gate behind proven Tier-1 retention.

## 4. PLAN B -- "FULL 3D PORT" (V3+), when credits/art re-upped (do NOT start until V2 retention proven + art budget funded)
- **V3 -- 3D world + art redo.** Battlefield decision: KEEP the 2.5D battler (cheapest, preserves the juiced feel + all card art) vs 3D battlefield (massive art+engine cost, risks the proven feel). **Recommendation: 2.5D battlefield persists into V3; only the WORLD goes 3D first.** On-chain economy maturation (the Gods-Unchained token decision) here, with regulatory counsel.
- **V4 -- app + metaverse.** Native app wrapper, UGC creator economy (Roblox-style), deeper social/metaverse.

## 5. INPUT SCHEME (hub, from input research)
Auto-detect input. Keyboard: Vim h/j/k/l + WASD + arrow keys all map to move; remappable. Touch: tap-to-move default (walking is secondary) + an on-screen digital joystick / directional arrows option. (Full output: task wrz0okilk.)

## 6. SEQUENCING + RISKS
Build order: Phase 0 (validate feel) -> Phase 1 (the 80%-value static hub) -> Phase 2/3/4 (social/arcade/economy, reusing STAGED systems) -> Phase 5 (walkable plaza) only if Tier-1 retention proves out. Risks: mobile perf of a live plaza (gate it), regulatory exposure on any on-chain token (cosmetics-only in V2 sidesteps it), scope creep. Every version merges via the sole-deployer e5 ~/ak_deploy path + git checkpoints; never breaks the live battler. Most of V2 REUSES already-built/staged AK systems (social_layer.sql staged, ak_grants live, Fortnite-layer GO'd, shop live on Stripe) -- V2 is largely WIRING, not building from scratch.
