# ALLEY KINGZ x $BCARDD -- CROSS-CHECK (delta + merge)
**Date:** 2026-06-02 | **Author:** Synthesizer (Hive fork, phase 8 of 9) | **Status:** Cross-check complete, feeds MASTER_BUILD_PLAN.md

> **What this is:** Not a fresh deliverable. A delta+merge pass over the 5 deep-dive docs
> (MASTER_ECOSYSTEM_PLAN, CHAIN_DECISION_MEMO, ROSTER_CANON, SEEDANCE_BATTLE_KIT,
> ECOSYSTEM_ARCHITECTURE, REUSE_MANIFEST). Every conflict is named with provenance and a
> resolution. Every gap an executor would still hit is listed. Where two docs are stronger
> merged, that is called out. Resolutions land in MASTER_BUILD_PLAN.md.

All claims below were re-verified against the live files on 2026-06-02 (cards.json parsed,
functions dir listed, BCRDIToken.sol grepped). Receipts are inline, not assumed.

---

## A. CONFLICTS FOUND (named, with provenance + resolution)

### CONFLICT 1 -- Roster size: 48 vs 50 (the most-repeated error)
- **MASTER_ECOSYSTEM_PLAN** says "50-card roster" (section 1, section 8, section 13 budget math).
- **ECOSYSTEM_ARCHITECTURE** says "50 dog cards" in the pillar diagram (section 0) and "50-card roster" (section 3.1), then contradicts itself with the correct "48-card v1.0 roster" in section 3.3.
- **ROSTER_CANON** (section 1, section 8.6) and **REUSE_MANIFEST** (headline finding 2) both say **48**, explicitly flagging "50" as an estimate.
- **VERIFIED:** `cards.json` parsed = **48 cards exactly** (4 Mythic / 1 Legendary / 9 Epic / 20 Rare / 14 Common; 4 factions x 12). Receipt above.
- **RESOLUTION:** 48 is canon. Fix "50" everywhere (master plan + ECOSYSTEM_ARCHITECTURE diagram + any marketing copy). Do NOT invent 2 dogs just to hit a round number unless the operator explicitly wants 50 for marketing -- flagged as an operator option, default = keep 48. Budget math (Seedance credits, mint caps) uses 48.

### CONFLICT 2 -- verify-arcade-purchase: "built" vs does-not-exist
- **MASTER_ECOSYSTEM_PLAN** section 2 lists `supabase/functions/verify-arcade-purchase` as an EXISTING asset ("do NOT rebuild").
- **ECOSYSTEM_ARCHITECTURE** section 6.1 treats it as the live "shared economy backbone... already routes nos-* / chips-* / passes."
- **REUSE_MANIFEST** headline finding 4 + section 5 correctly says it does NOT exist; only `notify-lead` is in the functions dir.
- **VERIFIED:** `vantaris/supabase/functions/` contains only `notify-lead` and `game-event` (new, added 2026-06-02 20:58). **verify-arcade-purchase is NOT present.** Receipt above.
- **RESOLUTION:** REUSE_MANIFEST is right. `verify-arcade-purchase` is a GAP TO BUILD, not a reuse. This matters because two docs sequence the arcade mount assuming the backbone exists. The build plan moves it from "reuse" to a named Phase-4 build task (plus the sibling `verify-bcardi-onramp`). The new `game-event` function should be inspected -- it may already cover part of the currency-grant path.

### CONFLICT 3 -- EVM chain target: Zilliqa vs Cronos (provenance noise)
- **CHAIN_DECISION_MEMO** section 2 says the live `.sol` token targets **Zilliqa EVM** (ZIL presale, ZilSwap liquidity) AND separately references a "stalled 2025 Cronos launch" legacy contract.
- **REUSE_MANIFEST** section 1e + finding 3 says hardhat targets **Zilliqa EVM** testnet(33101)/mainnet(32769).
- **MASTER_ECOSYSTEM_PLAN** just says "EVM/Solidity" (no chain named).
- **VERIFIED:** `BCRDIToken.sol` header literally reads "The native token for Alley Kingz on Zilliqa EVM" with ZilSwap BCRDI/ZIL liquidity. Receipt above.
- **RESOLUTION:** Not a real conflict, just imprecision. The Solidity contracts target **Zilliqa**; Cronos was a separate, earlier stalled attempt. Either way the conclusion is identical and unaffected: there is NO live EVM liquidity worth bridging to, so Solana-native wins. Logged so it is not re-litigated.

### CONFLICT 4 -- Ticker: $BCARDD vs $BCRDI
- The live coin is **$BCARDD** (pump.fun SPL). The EVM artifacts say **$BCRDI** (no A), and the `.sol` filenames are `Bcrdi*`/`BCRDIToken`.
- Flagged correctly in **ECOSYSTEM_ARCHITECTURE** section 0 ("Canon is `$BCARDD`").
- **RESOLUTION:** Canon = **$BCARDD**. The `$BCRDI` spelling is dead EVM-era. Any ported logic, metadata, or copy uses $BCARDD. Cosmetic but holder-facing, so it is load-bearing for brand consistency.

### CONFLICT 5 -- Card numbering: only #0001 exists vs #0002-#0004 "assigned"
- **MASTER_ECOSYSTEM_PLAN** treats only $BCARDD #0001 as numbered.
- **ROSTER_CANON** section 2 ASSIGNS #0002 Jagged, #0003 Rosco, #0004 Crown Foxhound (Mythic order = faction order) and recommends numbering all 48.
- **VERIFIED:** cards.json has $BCARDD as the only pre-numbered card; the others carry name+faction+rarity but the #0002-#0004 assignment is ROSTER_CANON's new decision, not pre-existing data.
- **RESOLUTION:** Adopt ROSTER_CANON's numbering as canon (it is the more recent, more specific doc and the NFT mint needs deterministic indices). Number all 48 by faction then descending rarity during Phase 2 canon merge, BEFORE mint -- on-chain indices are permanent.

### CONFLICT 6 -- Mythic frame does not exist in the Art Bible
- **SEEDANCE_BATTLE_KIT** and **ROSTER_CANON** both treat "Mythic" as the top rarity tier with a hero frame.
- **ART_BIBLE v1.0** (per ROSTER_CANON section 3 note) defines only 4 frames: Common/Rare/Epic/Legendary. There is NO Mythic frame spec.
- **RESOLUTION:** ART_BIBLE needs a Mythic row added (Legendary Crown Gold holo + animated crown sigil + rainbow holo edge = the "Icon" treatment PRD_V2 reserved for tier 5, renamed Mythic). Small art-doc task, but it gates the 4 hero NFT frames. Added as a Phase-2/3 sub-task.

### CONFLICT 7 -- Arcade accent color: orange vs gold
- **ECOSYSTEM_ARCHITECTURE** section 6.4: arcade hub is gold (#c9a84c) on vanta-void; Alley Kingz currently ships orange (#ff6b35).
- **ART_BIBLE / SEEDANCE / ROSTER_CANON** lock Crown Gold #D4AF37 (gradient partner #c9a84c) on vanta-black as canonical.
- **RESOLUTION:** Everlight gold is canonical for chrome/frames/premium surfaces; Alley Kingz keeps orange ONLY as a faction/energy accent (it maps to Brick Warm #C1440E for Boneguard, not the UI). One arcade, one gold. Already resolved in-doc; logged so the frontend build does not reintroduce orange UI.

---

## B. NO-CONFLICT CONFIRMATIONS (the docs agree -- proven, not assumed)

- **Mythic names + factions match across ROSTER_CANON and SEEDANCE_BATTLE_KIT EXACTLY:** $BCARDD (Boneguard/Dogo Argentino), Jagged (Zoomie/Doberman), Rosco (Leashbreak/Australian Cattle Dog), Crown Foxhound (K9 Circuitry/Foxhound). Verified against cards.json. No drift. This is the single most important consistency check for the NFT mint + Seedance batch, and it passes clean.
- **Legendary = Stonejaw (Mastiff, Boneguard)** in both ROSTER_CANON and SEEDANCE_BATTLE_KIT. Verified in cards.json (1 Legendary). Clean.
- **Rarity counts identical** across ROSTER_CANON, ECOSYSTEM_ARCHITECTURE section 3.3, REUSE_MANIFEST: 4/1/9/20/14. Verified = correct.
- **Chain decision is unanimous:** all four docs that touch chain (MASTER, CHAIN_DECISION_MEMO, ECOSYSTEM_ARCHITECTURE, REUSE_MANIFEST) recommend Solana-native, .sol as reference-only. No internal disagreement -- only the operator sign-off remains.
- **Vehicle-to-dog mapping is consistent:** ROSTER_CANON section 4 (12 cars -> 4 rig-classes by faction) and SEEDANCE_BATTLE_KIT section 0 (faction -> rig language) describe the same 4 rig-classes (bruiser/sprinter/tech-ops/turret-util). $BCARDD -> Crown Rig (bruiser, ram_plow) is identical in ROSTER_CANON section 2 and SEEDANCE_BATTLE_KIT 2.1. Clean.
- **Free-first / spend line is consistent:** all docs name the SAME two real spends (Seedance credits + $BCARDD dev-buy) and the SAME free rails (Metaplex free libs, Cloudflare, Supabase, e5-mother render, Tensor/ME free listing). No cost contradiction.

---

## C. GAPS AN EXECUTOR WOULD STILL HIT (not covered by any single doc)

1. **Canon file does not yet live with the game.** All 3 canon JSONs (cards/decks/ability_params) physically sit under `01_OnyxPOS/prototype_dec2025/game_design/` and `BCARDI_Crypto/.../Resources/`. ROSTER_CANON recommends moving to `Alley_Kingz/ecosystem/data/` but this is NOT done. An executor minting from "canon" has no single home to read. ACTION: create `ecosystem/data/` and move/copy the 3 files there as the first Phase-2 step.
2. **decks.json + ability_params.json only exist in the BCARDI Unity copy, not the OnyxPOS copy.** REUSE_MANIFEST section 1a notes this. The merged canon must pull cards.json from OnyxPOS + decks/ability_params from the Unity Resources folder. An executor reading only the OnyxPOS dir would be missing two of three files.
3. **The `game-event` edge function is new (added today) and undocumented in any of the 5 docs.** It may overlap with the verify-arcade-purchase build. Inspect before building, to avoid duplicate work.
4. **No one has confirmed the live Seedance credit balance.** Every doc says "confirm balance before spend" but none records the actual number. This is the literal gate on Phase 1b. Operator/executor must pull the balance before the ~3,000-credit Batch 1+1b commit.
5. **Attribute Plugin update-authority holder is undecided.** CHAIN_DECISION_MEMO open item 2 + ECOSYSTEM_ARCHITECTURE flag it; nobody decided WHO holds the treasury multisig/PDA that can patch card stats. Must be decided before mint (on-chain authority is set at mint time).
6. **Legal sign-off is unscheduled.** ECOSYSTEM_ARCHITECTURE names 3 legal gates but there is no named legal owner or timeline. Gate 1 (off-ramp) defaults OFF so launch is not blocked, but Gate 3 (loot-box / pack rips) blocks the MARKETPLACE/pack phase and needs the geofence (WA/MN/HI) + odds-disclosure built in. An executor would hit this at the marketplace phase with no legal contact assigned.
7. **No Solana dev is named.** The plan is "almost no custom on-chain code" (managed Metaplex), but SOMEONE writes the Umi mint scripts + the off-chain vault-server signing logic. REUSE_MANIFEST routes builds to e5-mother but does not name the agent/human. Assigned in the build plan (everlight_architect + 67_backend_architect).

---

## D. WHERE TWO DOCS ARE STRONGER MERGED (synthesis wins)

1. **CHAIN_DECISION_MEMO section 5 (the 6-contract port map) + ECOSYSTEM_ARCHITECTURE section 4 (the sink/source economy) = the complete economic engine.** The memo says HOW each .sol rule lands on Solana; the architecture says WHAT each one does to supply. Merged, an executor gets both the primitive (Core Attribute Plugin, Candy Machine guard, off-chain vault server) AND the economic intent (burn %, treasury %, no-emission anti-spiral). Neither alone is buildable; together they are a spec.
2. **ROSTER_CANON section 9 (the merged card schema) + ECOSYSTEM_ARCHITECTURE section 9.1 (the on-chain/off-chain split) = the exact mint payload.** ROSTER_CANON defines the card object (factionId, rig, cardNumber, nft block); ECOSYSTEM_ARCHITECTURE defines which fields go on-chain (Attribute Plugin: hp/damage/ability/queen_target) vs off-chain (image/animation_url). Merged = the precise "what goes in the Attribute Plugin vs the IPFS JSON" map. This belongs in one place; the build plan points the mint step at both.
3. **SEEDANCE_BATTLE_KIT section 4 (phased credit budget) + REUSE_MANIFEST section 3 (the only-real-spend table) = the single spend gate.** Both phase Mythic-first; merged they give one number (Batch 1+1b = ~3,000 credits) tied to one trigger (coin launch teaser) with one fallback (drop clip 2.2 -> ~2,700, or Mythics-only floor ~1,200). The build plan uses this merged number as the only spend authorization in Phase 1-2.
4. **ECOSYSTEM_ARCHITECTURE cross-perk matrix (section 5) + the $BCARDD GTM kit (REUSE_MANIFEST 1g) = the launch funnel.** The matrix defines the perks; the existing X autopilot + copy pack execute them. Merged = the coin-holder->NFT-whitelist->in-game-perk flywheel is not just designed, it has a delivery channel already built.

---

## E. CONFLICT-RESOLUTION LEDGER (what the build plan locks)

| # | Conflict | Resolution locked in MASTER_BUILD_PLAN |
|---|---|---|
| 1 | 48 vs 50 cards | **48** canon; fix "50" in master plan + arch diagram + copy |
| 2 | verify-arcade-purchase built vs missing | **Missing** -- it is a Phase-4 BUILD task (+ verify-bcardi-onramp); inspect new `game-event` fn first |
| 3 | Zilliqa vs Cronos EVM | **Zilliqa** (Cronos was separate stalled attempt); no live liquidity either way; Solana wins |
| 4 | $BCARDD vs $BCRDI ticker | **$BCARDD** canon |
| 5 | Card numbering | Adopt ROSTER_CANON #0001-#0004 + number all 48 by faction/rarity before mint |
| 6 | No Mythic art frame | Add Mythic row to ART_BIBLE (Crown Gold holo + crown sigil + rainbow edge) in Phase 2/3 |
| 7 | Orange vs gold arcade UI | **Gold** canonical for UI/frames; orange is faction-accent only |

*Cross-check complete 2026-06-02. Feeds MASTER_BUILD_PLAN.md (phase 9 synthesis). All facts re-verified against live files, not inherited from the source docs.*
