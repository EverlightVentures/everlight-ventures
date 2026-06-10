# ALLEY KINGZ x $BCARDD -- MASTER BUILD PLAN (canonical)
**Date:** 2026-06-02 | **Author:** Synthesizer (Hive fork, phase 9 of 9) | **Status:** CANONICAL -- supersedes the 5 deep-dives for execution
**Synthesized from:** MASTER_ECOSYSTEM_PLAN_2026-06-02.md, CHAIN_DECISION_MEMO.md, ROSTER_CANON.md, SEEDANCE_BATTLE_KIT.md, ECOSYSTEM_ARCHITECTURE.md, REUSE_MANIFEST.md
**Conflicts resolved per:** CROSS_CHECK.md (section E ledger)

> **This is the ONE doc an executor reads.** It resolves every conflict the cross-check raised,
> sequences the build, names who/what builds each phase, and isolates the only real spend.
> The 5 source docs remain the deep reference; this is the decision-resolved spine.
> Provenance is cited per piece (which source doc it came from).

---

## 1. THE LOCKED CONCEPT (one paragraph, no longer up for debate)

**Alley Kingz is cyberpunk DOG crews piloting Twisted-Metal street war-rigs, fighting
Clash-Royale tower lanes with vehicular carnage.** $BCARDD -- a Dogo Argentino warlord -- is
the king of the pack: card **#0001 Mythic**, the **$BCARDD coin** mascot (Solana/pump.fun),
AND the **blackjack dealer**. One dog, one currency, one aesthetic (Crown Gold #D4AF37 on
vanta-black #050507), one arcade (Everlight Arcade on vantaris), metaverse later. The cards
ARE the NFTs; the chips ARE $BCARDD. *(Concept from MASTER_ECOSYSTEM_PLAN section 1;
aesthetic locked in SEEDANCE_BATTLE_KIT section 0 + ROSTER_CANON section 5.)*

**Dogs are the IP; vehicles are the toys.** The 48 dogs are the closed, ownable character
roster. The 12 cars from GAME_VISION fold in as the **rigs the dogs pilot** -- not separate
characters. *(ROSTER_CANON section 4 + MASTER Decision B.)*

---

## 2. THE TWO GATING DECISIONS (recommended answers + why)

These two block everything downstream. Both are unanimous across the source docs; only operator
sign-off remains.

### DECISION A -- CHAIN = **SOLANA-NATIVE** (recommended, lock it)
**Answer: Go Solana-native. One Phantom wallet holds $BCARDD + every Alley Kingz NFT.**
- 48 playable stat-cards = **Metaplex Core** assets with the **Attribute Plugin** holding
  hp/damage/ability/queen_target ON-CHAIN (readable by the game + marketplace, mutable only by
  the update authority, not the owner). *(CHAIN_DECISION_MEMO section 4a.)*
- High-volume tail (commons + the 10k cosmetic Genesis dogs from AlleyKingzDogs.sol) =
  **Bubblegum V2 compressed NFTs** (~$0.001/mint). *(CHAIN_DECISION_MEMO section 4c.)*
- The six `.sol` contracts stay as **reference logic only** -- port the rules, never redeploy
  the bytecode. *(CHAIN_DECISION_MEMO section 5 port map.)*
- **Why:** the load-bearing fact is the EVM token is already DEAD -- `BCRDIToken.sol` targets
  **Zilliqa EVM** (verified in the file header), there is NO live liquidity to bridge to, and a
  bridge is the #1 exploit surface in crypto. Solana = one wallet, ~$0.70/card mint, on-chain
  stats a program can read, one holder story ("buy the coin, hold the cards, all in Phantom").
  There is no column where EVM+bridge wins. *(CHAIN_DECISION_MEMO sections 2, 3.)*

### DECISION B -- ROSTER = **DOGS PILOT RIGS, 48 CARDS** (recommended, lock it)
**Answer: The 48 cyberpunk dogs are the character roster (4 factions x 12). The 12 cars are the
Twisted-Metal rigs they pilot. $BCARDD #0001 threads coin + card + dealer.**
- 4 factions: **Boneguard Crew, Zoomie Syndicate, Leashbreak Tactix, K9 Circuitry** (12 each).
- 4 Mythics (one per faction): **$BCARDD #0001, Jagged #0002, Rosco #0003, Crown Foxhound #0004.**
  1 Legendary: **Stonejaw.** *(ROSTER_CANON sections 1-2; VERIFIED against cards.json.)*
- **Roster size = 48, NOT 50** (CROSS_CHECK conflict 1; cards.json parsed = 48 exactly).
  Fix every "50" in the old docs + marketing.
- **Why:** dogs are the through-line to the coin/dealer (the whole point); the cars deliver the
  vehicular carnage Rich wants without diluting the character IP or breaking NFT scarcity (the
  roster stays closed; the Chop Shop breeds RIGS, never dogs). *(ROSTER_CANON section 4.)*

**Everything below assumes A + B locked. Flip either and the plan forks.**

---

## 3. THE FIVE-PILLAR MAP

```
                        $BCARDD (Solana / pump.fun)
                    the currency AND the mascot dog ($BCARDD)
                                |
   +------------+--------------+--------------+--------------+
 PILLAR 1     PILLAR 2       PILLAR 3       PILLAR 4       PILLAR 5
 THE COIN     THE GAME       THE NFTs       THE ARCADE     METAVERSE
 $BCARDD      Alley Kingz    48 dog cards   vantaris hub   (option, last)
 chip+fuel    dog crews +    = playable     blackjack +    avatars + rigs
 fixed 1B     TM war-rigs    on-chain stat  AK + 6 games   3D, same wallet
 buyback-burn no P2W         Genesis caps   ONE wallet     never a dependency
```

**How they feed each other** *(ECOSYSTEM_ARCHITECTURE sections 4-5):*
- **Coin -> everything:** $BCARDD is the settlement layer (the chip in blackjack, soft/hard
  currency in Alley Kingz, the buy/sell token for NFTs). Fixed 1B supply, no emission. Creator
  fees fund weekly discretionary buyback-burn + treasury.
- **NFT = the card:** owning the $BCARDD NFT = owning the playable Mythic with on-chain stats.
  NFT adds ownership/tradeability/scarcity/cosmetic OG-perks -- **never raw power** (no P2W).
- **Game -> NFT demand:** scarcity (Mythic/Genesis caps) drives floor; people want the cards.
- **Arcade = front door:** one identity (`player_accounts`), one Phantom wallet, two funding
  doors (Stripe fiat + $BCARDD on-ramp) feeding the same Supabase `game_currencies` balance.
- **Metaverse = roof:** same assets/wallet/NFT rendered in 3D later. Upside, not prerequisite.

**Two-layer money (do NOT collapse):** $BCARDD is the on-chain SETTLEMENT layer; chips/NOS/Gems
are off-chain TABLE credits. The off-ramp (table value -> $BCARDD) stays DISABLED until Legal
Gate 1 signs. This keeps the coin a utility and the games non-gambling. *(ECOSYSTEM_ARCHITECTURE
section 1 -- the single most important design decision.)*

---

## 4. SEQUENCED PHASED ROADMAP (coin first; do NOT parallelize the spend)

Sequencing rule from MASTER section 9: the coin ships first (it is closest + funds + audiences
the rest), then hero art, then canon+mint, then playable, then full set+market, then metaverse.

### PHASE 0 -- LOCK (operator, ~1 day)
- Operator signs Decision A (Solana) + Decision B (dogs/48) + legal posture A (utility/cosmetic).
- **Builds:** nothing. **Who:** Rich + `40_strategic_modeler` + `everlight_architect`.
- **Output:** this doc's section 9 checked off. Unblocks all NFT work.

### PHASE 1 -- COIN (already in flight, parent session)
- Launch $BCARDD on pump.fun (1B fixed, ~9% dev-buy, Phantom seed in Proton Pass, creator-fee
  -> buyback-burn). *(REUSE_MANIFEST 1g; BCARDI_SOLANA_RELAUNCH_SPEC.)*
- **Builds:** the coin (parent owns this). **Who:** Rich (keys; AI never signs) + the existing
  X autopilot / GTM kit. **Reuse:** `BCARDI_Crypto/00_Core` + `02_Community` kits, coin art,
  the shipped dealer video.

### PHASE 2 -- SEEDANCE MYTHIC TEASER + CANON MERGE (parallel art + data; ~3,000 credits)
- **2a Art (Seedance):** generate Batch 1 + 1b = **4 Mythic hero clips + $BCARDD coin-tie idle +
  5-clip war trailer (T1-T5)** = the entire launch/hype kit. *(SEEDANCE_BATTLE_KIT sections 2-4.)*
  - **Who:** `63_ui_ux_designer` + `everlight_content_director`, through `VISUAL_AI_PIPELINE_SOP`
    Stage-4 Art Review Gate (mandatory, no slop). **Render:** e5-mother (phone proot cannot).
  - **Reuse:** ART_BIBLE palette, PROMPT_BIBLE spine, the proven Blackjack Seedance precedent,
    `content_pack.json` as the asset ledger (currently empty -- clips fill it).
  - **Add:** the Mythic art frame to ART_BIBLE (Crown Gold holo + crown sigil + rainbow edge --
    CROSS_CHECK conflict 6).
- **2b Canon merge (data):** create `Alley_Kingz/ecosystem/data/`; move cards.json (OnyxPOS) +
  decks.json + ability_params.json (BCARDI Unity copy -- the OnyxPOS copy lacks the latter two)
  into it as the permanent home. Number all 48 cards by faction/rarity ($BCARDD #0001 ...).
  Archive the 2 human-crew GameData.json drafts via `memory_pipeline.ingest_before_delete()` ->
  `08_BACKUPS/archived_prototypes/`. Flag Unity Resources JSONs as generated mirrors.
  *(ROSTER_CANON section 7; CROSS_CHECK gaps 1-2.)*
  - **Who:** `61_saas_factory_lead` + `67_backend_architect`.
- **Output:** the hype kit ships as the coin teaser + NFT preview; the single canon data set
  exists with deterministic mint indices. **This must finish before any mint (on-chain forever).**

### PHASE 3 -- SOLANA NFT MINT (Genesis flagship set)
- Create the Metaplex Core collection on **e5-mother** via Umi + mpl-core (phone cannot npm).
  Write the 48 cards' gameplay stats into the **Attribute Plugin** (on-chain); push image +
  Seedance `animation_url` to IPFS/web3.storage free tier (Arweave/Irys only for Mythic heroes).
  Mythics first ($BCARDD #0001), matching the Seedance phasing. *(CHAIN_DECISION_MEMO section 8.)*
- Candy Machine v3 (Sugar) with the **$BCARDD SPL payment guard + coin-holder allowlist** + per-
  card Genesis caps (Mythic 100 / Legendary 500 / Epic 2k / Rare 10k / Common uncapped via cNFT).
  *(ECOSYSTEM_ARCHITECTURE section 3.3.)*
- **Who:** `everlight_architect` + `67_backend_architect` (Solana dev path). **Verify:** read
  attributes back via Helius DAS free tier -- PROVE stats are on-chain (receipt, not a claim).
- **Reuse:** `nft_metadata_template.json` as the off-chain JSON schema; the .sol fee/rarity/
  genesis-lock rules as the port spec. **Free libs:** mpl-core, mpl-bubblegum, Sugar, Umi.

### PHASE 4 -- ARCADE PLAYABLE (web-first, the front door)
- Build the missing `verify-arcade-purchase` Supabase edge function (it does NOT exist -- only
  `notify-lead` + a new `game-event` do; inspect `game-event` first for overlap). Add sibling
  `verify-bcardi-onramp` (Solana tx -> grants NOS/chips/Gems via the same `game_currencies`
  writes). Add `solana_wallet` column to `player_accounts` + a shared wallet-connect component.
  *(ECOSYSTEM_ARCHITECTURE section 6.3; CROSS_CHECK conflict 2 -- this is a BUILD, not a reuse.)*
- Mount **game_v8 (Three.js)** at `/play/alley-kingz` (marketing stays at `/alley-kingz`),
  add to the arcade GAMES grid as BETA. NFT-card read path: query the connected Phantom's
  Metaplex assets, match `Name` to cards.json, mark owned cards (tradeable + OG perks) on top of
  off-chain `unlockedCardIds`. *(ECOSYSTEM_ARCHITECTURE section 6; REUSE_MANIFEST 1f.)*
- **Who:** `62_frontend_architect` + `64_component_engineer`. **Build path:** e5-mother
  (`next build`), deploy artifact to Cloudflare Pages. **UI is GOLD, not orange** (CROSS_CHECK 7).
- **Reuse:** game_v8 + combat_upgrades.js + graffiti_system.js, the arcade hub, Supabase schema.

### PHASE 5 -- FULL SET + MARKETPLACE (phased, demand-gated)
- Seedance Batch 2 (Stonejaw + 8 Epics, ~2,700 credits), then Batch 3-4 (Rare/Common tail) ONLY
  as game/marketplace demand justifies -- never bulk-buy. *(SEEDANCE_BATTLE_KIT section 4.)*
- List on **Tensor / Magic Eden** in $BCARDD (free to list) BEFORE writing any custom Anchor
  escrow -- FREE-FIRST. Build the fee-burning Anchor market only if a $BCARDD-denominated
  deflationary market becomes a hard requirement. *(CHAIN_DECISION_MEMO section 6 item 6.)*
- Port the `BcrdiGameVault.sol` arena/halving/daily-cap math into an off-chain server signing
  $BCARDD prize transfers (skill-gated, keys never on the AI side). *(CHAIN_DECISION_MEMO 5.)*
- **Legal Gate 3 (loot-box/pack-rips) must sign before paid packs ship:** geofence WA/MN/HI,
  disclose odds. *(ECOSYSTEM_ARCHITECTURE section 8.)*
- **Who:** `everlight_architect` + `67_backend_architect` + `74_growth_engineer` (cross-promo).

### PHASE 6 -- METAVERSE (option layer, last, never a dependency)
- Unity ArenaAdvance mobile/3D release, then avatars + rigs as 3D assets reusing the SAME
  wallet/NFT/$BCARDD identity. Build on AceMagician PC (phone cannot build Unity).
  *(ECOSYSTEM_ARCHITECTURE section 7; REUSE_MANIFEST 2c.)* If it never ships, the economy is
  already a complete closed loop (coin + game + NFT + arcade).

---

## 5. THE FREE-FIRST COST LINE (only two real spends)

FREE-FIRST law applied: existing infra -> self-host -> free tiers -> build, before any paid path.
*(REUSE_MANIFEST section 3; SEEDANCE_BATTLE_KIT section 4.)*

| # | Spend | Amount | Gate |
|---|---|---|---|
| 1 | **Seedance credits** | Batch 1+1b = **~3,000 credits** (4 Mythics + coin-idle + 5 trailer clips). Fallback: drop clip 2.2 -> ~2,700; floor = 4 Mythics only ~1,200. Full 48-set ~14,400 -- NEVER bulk. | **Confirm live credit balance BEFORE the commit** (no doc records it -- CROSS_CHECK gap 4). |
| 2 | **$BCARDD dev-buy** | ~9% of supply + ~$2 pump.fun deploy + cents of SOL gas/mint rent | Already planned in the parent session. An investment, not a tool cost. |

**Everything else = $0:** Metaplex Core/Bubblegum/Sugar/Umi (free libs), Phantom + wallet-adapter
(free), Helius + web3.storage (free tiers), Cloudflare Pages + Supabase (existing), e5-mother +
AceMagician render (existing infra), Tensor/Magic Eden listing (free), Solana devnet test (free).
Mint rent is cents (~$0.70/Core card x 48 = ~$34; ~$10-100 for 10k cNFT dogs).

---

## 6. LEGAL GUARDRAILS (utility/fun, NEVER promised returns)

Absolute rule from the launch spec: **market as utility + fun, never as an investment with
promised returns.** Three gates need legal sign-off before the relevant surface ships
*(ECOSYSTEM_ARCHITECTURE section 8):*

| Gate | Trigger | Default until signed |
|---|---|---|
| **Gate 1 -- off-ramp** | Any in-game-value -> $BCARDD redemption (= gambling cash-out / money transmission) | **Off-ramp DISABLED.** On-ramp + $BCARDD-only marketplace + skill-gated prizes only (Option A). Evolve to gated off-ramp in season 2 only after sign-off + token trade-history depth. |
| **Gate 2 -- promised returns** | Buyback cadence, staking, "hold to earn", yield language | No promised amounts. Buyback = discretionary treasury action. No staking-for-yield. Hold-for-whitelist = access (OK); hold-for-yield = BANNED (Howey). |
| **Gate 3 -- loot-box / pack rips** | Paid packs with random tradeable outcomes | **Loop legal BEFORE the marketplace/pack phase (Phase 5).** Geofence WA/MN/HI, disclose odds. |

**Standing rules:** rewards skill-gated not time-gated; Everlight never runs a USD cash-out desk;
AI never touches keys or signs on-chain (all on-chain actions are Rich's); disclaimer on every
surface ("$BCARDD is a community meme coin inspired by $BCARDD the dog. Not affiliated with
$BCARDD Limited. In-game items/tokens are for entertainment and utility, not investments. No
promised returns."). **Recommended launch posture: Option A (Pure Utility + Cosmetic)** -- strongest
legal footing, ~14 days to clean, no off-ramp desk, marketplace in $BCARDD only.

---

## 7. CONFLICTS RESOLVED (from CROSS_CHECK section E -- all closed in this plan)

1. **48 not 50 cards** -- canon = 48; "50" corrected everywhere.
2. **verify-arcade-purchase missing** -- moved to a Phase-4 BUILD task (+ verify-bcardi-onramp).
3. **Zilliqa (not Cronos) EVM** -- noise resolved; no live liquidity either way; Solana wins.
4. **Ticker = $BCARDD** (not $BCRDI) -- canon for all ported logic/copy.
5. **Card numbering** -- ROSTER_CANON #0001-#0004 adopted; number all 48 before mint.
6. **Mythic art frame** -- add to ART_BIBLE in Phase 2/3.
7. **Arcade UI = gold** (not orange) -- orange is faction-accent only.

All seven are resolved (no remaining flags-with-recommendation; the only open items are operator
DECISIONS in section 9, not unresolved conflicts).

---

## 8. WHO/WHAT BUILDS EACH PHASE (one-line index)

| Phase | Lead agents | Key reused asset |
|---|---|---|
| 0 LOCK | Rich + 40_strategic_modeler + everlight_architect | this plan |
| 1 COIN | Rich (keys) + X autopilot/GTM kit | BCARDI_Crypto launch + community kits |
| 2 ART | 63_ui_ux_designer + everlight_content_director | ART_BIBLE, PROMPT_BIBLE, SOP, content_pack.json, Blackjack Seedance precedent |
| 2 CANON | 61_saas_factory_lead + 67_backend_architect | cards.json + BCARDI decks/ability_params |
| 3 NFT | everlight_architect + 67_backend_architect | nft_metadata_template.json, .sol port map, free Metaplex libs |
| 4 ARCADE | 62_frontend_architect + 64_component_engineer | game_v8 (Three.js), arcade hub, Supabase schema |
| 5 SET+MARKET | everlight_architect + 67_backend_architect + 74_growth_engineer | Tensor/ME free listing, BcrdiGameVault port, cross-perk matrix |
| 6 METAVERSE | (deferred) AceMagician build path | Unity ArenaAdvance |

All heavy builds (Seedance render, Node/Umi mint scripts, next build, Unity) run on
**e5-mother or AceMagician, NEVER the phone proot** (HARD LAW: proot SIGSEGVs on npm + cannot
render heavy media). *(REUSE_MANIFEST 2c.)*

---

## 9. OPERATOR: DECIDE THESE 8 THINGS TO UNBLOCK THE BUILD

1. **Chain (gates everything):** Solana-native NFTs (Metaplex Core + Bubblegum), .sol = reference
   only. **RECOMMEND: YES, Solana.** -> unblocks Phase 3.
2. **Roster (gates art + mint):** dogs-pilot-rigs, **48 cards**, Mythics $BCARDD/Jagged/Rosco/
   Crown Foxhound. **RECOMMEND: YES** (and accept 48, do not pad to 50). -> unblocks Phase 2-3.
3. **Legal posture:** ship **Option A** (pure utility/cosmetic, off-ramp OFF, $BCARDD-only
   marketplace, skill-gated prizes). **RECOMMEND: A.** -> sets the whole legal default.
4. **Seedance Batch 1 budget:** fund **~3,000 credits** (4 Mythics + coin-idle + 5 trailer clips).
   **RECOMMEND: yes, after confirming live credit balance** (the one number no doc has). Fallback
   ~2,700 or floor ~1,200. -> unblocks Phase 2a.
5. **Attribute-Plugin update authority:** who holds the treasury multisig/PDA that can patch card
   stats? **RECOMMEND: a treasury multisig the game controls, no single hot key.** Must be set
   AT mint. -> blocks Phase 3 if undecided.
6. **Build-target-first:** **web-first (game_v8 in the arcade)** before Unity mobile.
   **RECOMMEND: web-first.** -> sets Phase 4 scope.
7. **Marketplace:** **list on Tensor/Magic Eden in $BCARDD first**; custom Anchor escrow only if a
   $BCARDD-denominated deflationary market becomes required. **RECOMMEND: aggregators first.**
8. **Legal owner + timeline for Gate 3** (loot-box/pack-rips) -- needed before Phase 5, not before
   launch. **RECOMMEND: assign a legal contact now so Phase 5 is not blocked later.**

Decisions 1-4 unblock the immediate build (coin teaser + canon + Mythic mint). 5-8 are needed by
their respective phases. Nothing else is waiting on the operator.

---

*Synthesized 2026-06-02 (phase 9 of the Hive 9-phase doctrine). Resolves every CROSS_CHECK
conflict. The 5 deep-dive docs remain the reference; this is the decision-resolved spine an
executor follows. Next: operator checks section 9, parent launches Phase 1 (coin) -> Phase 2.*
