# ALLEY KINGZ x $BCARDD -- Master Ecosystem Plan
**Date:** 2026-06-02 | **Author:** Hive fork (audit + synthesis) | **Status:** Draft master plan for operator review

> **The Goal (one sentence):** One dog, one currency, one aesthetic, one arcade -- a Twisted-Metal x Clash-Royale cyberpunk dog-crew battler whose cards ARE the NFTs, whose chips ARE $BCARDD, that lives inside Everlight Arcade on the website today and grows into a metaverse tomorrow.

---

## 1. THE BIG INSIGHT (what ties it all together)

The pieces already rhyme -- they were just never connected:
- **$BCARDD** = the coin (Solana/pump.fun, from the 2026-06-02 launch plan) AND a real dog AND the blackjack dealer.
- **$BCARDD the Dogo Argentino** = **card #0001, Mythic, in `cards.json`** -- already statted (HP 2600, "Crownbreaker", can target Queen).
- **Alley Kingz** = a Clash-Royale-DNA lane battler with a 50-card **cyberpunk dog roster** already designed.
- **Twisted Metal** = the missing layer Rich wants: vehicular carnage. The dogs do not just run -- **the crews pilot battle rigs**, lanes are streets, towers go down in Twisted-Metal explosions.

**The unifying concept:** *Alley Kingz is cyberpunk dog crews piloting street war-machines, fighting Clash-Royale tower lanes with Twisted-Metal carnage. $BCARDD is the king of the pack -- the same dog you hold as a coin, the same dog who deals your blackjack.* One mascot threads the coin, the casino, the card game, and the NFTs.

---

## 2. AUDIT -- what already exists (do NOT rebuild)

| Asset | Location | State |
|---|---|---|
| Game vision (CAR direction) | `Alley_Kingz/research/GAME_VISION.md` | 12-car roster, Chop Shop breeding, monetization stack |
| **Card roster (DOG direction) -- 50 cards** | `01_OnyxPOS/prototype_dec2025/game_design/cards.json` | 4 factions, full stats/abilities, $BCARDD = #0001 |
| Art Bible v1.0 | `Alley_Kingz/ART_BIBLE.md` | Locked palette, rarity tiers, hyper-real SOP |
| Prompt Bible + Visual AI Pipeline SOP | `Alley_Kingz/PROMPT_BIBLE.md`, `VISUAL_AI_PIPELINE_SOP.md` | 6-stage gen->review->perf pipeline |
| Unity build | `Alley_Kingz/Alley_Kingz/ArenaAdvance/` | "ArenaAdvance" Unity project + GameData.Json |
| HTML prototypes v4-v8 | `Alley_Kingz/Alley_Kingz/prototype/` | Playable browser builds, combat upgrades, graffiti system |
| **NFT contracts (EVM)** | `Alley_Kingz/blockchain/contracts/` | `AlleyKingzCards.sol`, `AlleyKingzDogs.sol`, `AlleyKingzMarketplace.sol` + hardhat |
| NFT metadata template | `01_OnyxPOS/.../nft_metadata_template.json` | image + **animation_url** + on-chain stat attributes (video-NFT ready) |
| Seedance pipeline precedent | `Everlight_Gaming/Blackjack/SEEDANCE_ART_BRIEF.md` | Proven: Seedance Video 1.0 Pro, ~300 credits/3-4s clip; BCARDI dealer video already shipped |
| Specs | `Alley_Kingz/spec/PRD_V2.md`, `05_DATA_MODEL.md`, `PACK_RIP_OUTCOME_MODEL.md` | Product + pack-economy specs |
| Arcade hub | `vantaris/src/app/arcade/`, `vantaris/src/app/alley-kingz/`, `supabase/functions/verify-arcade-purchase` | Website arcade + purchase verification |
| Unity/BCARDI fusion | `BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/{cards,decks,ability_params}.json` | BCARDI already wired into a Unity card set |
| $BCARDD coin | `BCARDI_Crypto/00_Core/BCARDI_SOLANA_RELAUNCH_SPEC...` | Solana/pump.fun launch plan (parent session) |

---

## 3. TWO STRATEGIC DECISIONS THAT GATE EVERYTHING (operator call)

**DECISION A -- Chain unification.** The coin is **Solana** ($BCARDD/pump.fun). The NFT contracts are **EVM/Solidity**. A split ecosystem confuses holders and doubles the work.
- **Recommended:** go **Solana-native for the NFTs** (Metaplex Core / compressed NFTs -- cheap mints, same wallet as the coin, one Phantom for everything). Keep the `.sol` files as battle-tested reference logic. One chain = one wallet = one story = mass-psychology clean.
- Alt: keep EVM NFTs + bridge. More surface area, more to break. Not recommended for a hands-off founder.

**DECISION B -- Dogs, cars, or both.** Two rosters exist (50 dogs vs 12 cars).
- **Recommended:** **Dogs are the IP, vehicles are the toys.** The crews are dog characters ($BCARDD etc.); they pilot Twisted-Metal rigs in battle. This keeps the BCARDI dog as the through-line to the coin/dealer AND delivers the vehicular carnage Rich wants. The car roster folds in as the *vehicles the dogs drive*, not separate characters.

Everything below assumes Recommended A + B. Flip either and the plan forks.

---

## 4. THE FIVE INTERTWINED PILLARS

```
                    $BCARDD (Solana) -- the currency + the mascot dog
                                |
   +----------------+----------------+----------------+----------------+
   |                |                |                |                |
 COIN            CARD GAME         NFT SET          ARCADE          METAVERSE
 (pump.fun)     (Alley Kingz)    (dog cards)     (website hub)     (long-term)
 chips/utility   play-to-earn     = the cards     blackjack +       avatars +
 buyback-burn    cyberpunk dogs   Seedance video  Alley Kingz +     rigs become
 funds rewards   + TM vehicles    on-chain stats  6 Vantaris games  3D assets
```

**How they feed each other:**
1. **Coin -> everything:** $BCARDD is the chip in blackjack, the soft currency in Alley Kingz, the buy/sell token for NFT cards. Creator-fee + treasury buyback-burn funds tournaments + airdrops.
2. **NFT = the card:** owning the $BCARDD NFT = owning the playable Mythic card with on-chain stats (the `nft_metadata_template.json` already encodes HP/damage/ability). True ownership, tradeable on the marketplace contract.
3. **Game -> NFT demand:** people want the cards to win; scarcity (Mythic/Legendary) drives floor.
4. **Arcade = the front door:** everलight Arcade on the website hosts blackjack (live, BCARDI dealer), Alley Kingz, and the 6 Vantaris games -- all sharing the $BCARDD wallet + identity.
5. **Metaverse = the roof:** the dog crews + their rigs are already 3D-destined (Unity); later they become metaverse avatars/vehicles. Build the startup now, the metaverse is the option, not the dependency.

---

## 5. THE NFT COLLECTION + SEEDANCE BATTLE-VIDEO PLAN (the part Rich asked for)

**Collection = the 50 dog cards in `cards.json`, Solana-native, animated.** Each NFT's `animation_url` = a **Seedance Twisted-Metal battle clip** of that dog-crew rig in war.

**Rarity ladder (from cards.json, drives mint scarcity + Seedance budget priority):**
- **Mythic (4):** $BCARDD (#0001), Jagged, Rosco, Crown Foxhound -- *cinematic hero videos first.*
- **Legendary (1+):** Stonejaw ... -- hero treatment.
- **Epic / Rare / Common:** batch video, shorter clips.

**Seedance production model (proven by the Blackjack brief):**
- Engine: **Seedance Video 1.0 Pro**, 3-4s clips, ~300 credits each.
- **Phase the spend:** 4 Mythics first (~1,200 credits) = the hype trailer set, then Legendary/Epic, then the long tail. 50 full videos approx 15,000 credits -- do NOT do all at once; gate by what the game/marketing needs.
- **Prompt spine (Twisted Metal x Clash Royale, per ART_BIBLE):** cyberpunk street, golden-hour-or-neon-night, hyper-real PBR, the dog-crew piloting an armored street rig, muzzle-flash + nitro + debris, lane charging a tower, 3-4s loop-ready, no text/watermark. $BCARDD = Dogo Argentino warlord in a crowned matte-black war rig, gold trim (ties to coin art).
- **War-scene set (Rich's "going to war / shooting each other / towers downhill"):** a separate batch of **battle-cinematic clips** (crew vs crew, rig vs tower collapse) for the trailer, the arcade hero loop, and social teasers -- same Seedance model, 16:9.
- **Pipeline already exists:** run through `VISUAL_AI_PIPELINE_SOP.md` (reference -> prompt -> generate -> Art Review Gate -> perf check -> repo + `content_pack.json`). Art Review Gate is mandatory -- no AI slop.

---

## 6. THE HIVE WORKFLOW TO BUILD IT (use all agents, the 9-phase doctrine)

Run as a multi-phase Workflow (parent launches; this fork only plans it):

- **Phase 1 -- LOCK (decisions A+B):** operator + `40_strategic_modeler` + `everlight_architect` resolve chain + dogs/cars. Output: 1-page decision memo.
- **Phase 2 -- CANON (single source of truth):** merge the car vision + dog roster + BCARDI Unity set into ONE `cards.json` + `decks.json` + `ability_params.json` canon. Owner: `61_saas_factory_lead` + `67_backend_architect`. Kill the duplicates (OnyxPOS copy vs BCARDI copy vs ArenaAdvance copy -- pick one path).
- **Phase 3 -- ART (parallel Seedance):** `63_ui_ux_designer` + `everlight_content_director` drive the Seedance Mythic-first batch through the Visual AI Pipeline SOP + Art Bible gate. Output: 4 Mythic hero videos + the war-trailer set.
- **Phase 4 -- CHAIN:** `everlight_architect` + a Solana dev path -- port the NFT logic to Metaplex (Solana), wire NFT stats = game card. $BCARDD as the marketplace currency. Re-verify against the eradication/compliance gates.
- **Phase 5 -- GAME:** `62_frontend_architect` + `64_component_engineer` take the best prototype (game_v8 / Unity ArenaAdvance) to a playable Arcade build with the new art + NFT-card binding.
- **Phase 6 -- ARCADE INTEGRATION:** mount Alley Kingz in `vantaris/src/app/arcade` next to blackjack; shared $BCARDD wallet + `verify-arcade-purchase`; one identity.
- **Phase 7 -- GTM:** `74_growth_engineer` + the X autopilot (already built for $BCARDD) cross-promote: coin holders get NFT whitelist, NFT holders get in-game perks, blackjack players see $BCARDD.
- **Phase 8 -- CROSS-CHECK + SYNTHESIZE:** per CLAUDE.md 9-phase doctrine -- agents review each other, one canonical build doc.
- **Phase 9 -- CONVERGE:** operator (Rich) signs off; log to Blinko.

---

## 7. FREE-FIRST + RESOURCE NOTES

- **Reuse, do not rebuild:** Unity ArenaAdvance, the HTML prototypes, the art/prompt bibles, the SOP, the arcade infra, the $BCARDD launch kit, the Vantaris site theme -- all already built.
- **Free/cheap rails:** Solana compressed NFTs (cents to mint thousands), Cloudflare Pages for the site, the existing e5-mother render path for heavy media (phone proot cannot do ffmpeg/Unity builds -- route to e5 or AceMagician).
- **Only real spend:** Seedance credits (phase it, Mythic-first) + the $BCARDD dev-buy (already planned). Everything else uses existing infra.

---

## 8. PHASED ROADMAP (startup now, metaverse later)

1. **Now:** launch $BCARDD (coin). Ship the 4 Mythic Seedance hero videos as the teaser + NFT preview.
2. **Next 30-60d:** canon merge + Solana NFT mint of the flagship set; Alley Kingz playable in Everlight Arcade with NFT-card binding.
3. **60-120d:** full 50-card video set (phased), marketplace live, $BCARDD as in-game/chip currency across blackjack + Alley Kingz.
4. **Later:** mobile store release (Unity), tournaments funded by treasury, then the metaverse layer (avatars + rigs).

---

## 9. HONEST GAPS / RISKS

- **Chain split is unresolved** -- EVM NFT contracts vs Solana coin. Until Decision A lands, NFT work is blocked.
- **Two rosters (car vs dog) are not merged** -- there are 3 divergent card files; pick canon or the game fragments.
- **Seedance at scale is the real cost** -- 50 hero videos approx 15k credits; must be phased, not bulk-bought (free-first law: confirm credit balance + per-clip cost before committing).
- **Phone cannot build Unity or render video** -- all heavy builds route to e5-mother / AceMagician (documented proot limits).
- **Scope is huge** -- this is 4 products (coin, game, NFT, arcade). Sequence them; do not parallelize the spend. The coin ships first (it is closest), it funds and audiences the rest.
- **Legal:** NFTs + a coin + gameplay utility raise the "is this a security" question higher than a pure meme coin. Keep the same guardrail (utility/fun, never promised returns); loop the legal team before the marketplace goes live.

---

## 10. OPERATOR DECISIONS DEFERRED

1. **Chain:** Solana-native NFTs (recommended) vs EVM + bridge.
2. **Roster:** dogs-pilot-vehicles fusion (recommended) vs dogs-only vs cars-only.
3. **Seedance budget:** how many hero videos to fund in batch 1 (recommend the 4 Mythics).
4. **Build target first:** ship Alley Kingz as a web Arcade build (fast) vs Unity mobile (bigger). Recommend web-first inside Everlight Arcade.

*Master plan compiled 2026-06-02 from the existing Alley Kingz, BCARDI_Crypto, Everlight_Gaming, and vantaris/arcade assets. Pairs with `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`. Next step: operator resolves Decisions A+B, then the parent launches the Phase 1-9 Hive workflow.*
