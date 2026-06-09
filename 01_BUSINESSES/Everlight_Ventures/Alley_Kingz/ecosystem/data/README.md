# ALLEY KINGZ -- CANONICAL CARD DATA (SINGLE SOURCE OF TRUTH)

**Status:** CANON LOCKED | **Date:** 2026-06-03 | **Owner:** Game Canon (Hive) / Amara Osei, Iron Stack
**Authority:** This directory is the ONE source of truth for Alley Kingz card data. Everything else is a generated mirror or an archived draft.

> **Locked decisions (operator):**
> - **Chain = Solana-native, Metaplex Core** (`standard: "metaplex-core"`). The EVM `.sol` contracts are reference-only (see bottom).
> - **Roster = dogs pilot rigs, 48 cards.** Dogs are the IP; the 12 GAME_VISION cars are the Twisted-Metal war-rigs the dog crews pilot, not separate characters.

---

## 1. THE FILES IN THIS DIRECTORY (canon)

| File | What it is |
|---|---|
| `cards.json` | The canonical **48-dog roster**. Every original card preserved verbatim, annotated with `meta`, `cardNumber`, `factionId`, `bodyArchetype`, `isMythic`, `rig`, `nft`. 4 factions x 12 = 48. |
| `decks.json` | The 4 faction starter decks (one per faction), references dogs by name. Carried forward unchanged. |
| `ability_params.json` | 2-ability rotation per dog + rarity scaling. Carried forward unchanged. |
| `nft_metadata_template.json` | The NFT shape ($BCARDD #0001 sample): Solana / Metaplex Core, `animation_url` + on-chain stat attributes (`hp`, `damage`, `ability`). |
| `_build_canon.py` | The deterministic builder that produced `cards.json` from the source roster. Re-runnable; it preserves all original fields and only ADDS the merge fields. |

### Top-level `meta` block in cards.json
```json
"meta": {
  "chain": "solana",
  "ticker": "$BCARDD",
  "standard": "metaplex-core",
  "cardCount": 48,
  "factions": ["Boneguard Crew", "Zoomie Syndicate", "Leashbreak Tactix", "K9 Circuitry"],
  "mythics": ["$BCARDD", "Jagged", "Rosco", "Crown Foxhound"],
  "legendary": ["Stonejaw"]
}
```

### What the merge ADDED to each card (no stats changed)
- `cardNumber` -- deterministic NFT mint index. $BCARDD is pinned **#0001**; the rest are numbered faction-order then descending-rarity (Mythic > Legendary > Epic > Rare > Common), so mint indices are stable.
- `factionId` -- machine key for `class` (`boneguard_crew`, `zoomie_syndicate`, `leashbreak_tactix`, `k9_circuitry`).
- `bodyArchetype` -- demoted PRD_V2 class, now a rig-body tag (`bruiser` | `sprinter` | `tech_ops` | `turret_util`).
- `isMythic` -- hero-set flag (drives Seedance batch + frame).
- `rig` -- the Twisted-Metal vehicle this dog pilots (a TOY, not a character): `name`, `rigClass`, `weaponMod`, `sourceCar`, `rigLanguage`, `skinnable`, `choppable`. The 4 Mythics carry their named signature rigs ($BCARDD = The Crown Rig, Jagged = Shadowblade, Rosco = The Jammer, Crown Foxhound = Railhound).
- `nft` -- `chain: solana`, `standard: metaplex-core`, `animation_url` (Seedance clip), `onchain_stats`.

---

## 2. PROVENANCE (what came from where)

| Output | Source |
|---|---|
| `cards.json` cards | `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/cards.json` (the 48-dog roster, $BCARDD #0001 pre-existed) |
| `decks.json` | same `game_design/decks.json` (byte-identical to the Unity copy) |
| `ability_params.json` | same `game_design/ability_params.json` (byte-identical to the Unity copy) |
| `nft_metadata_template.json` | same `game_design/nft_metadata_template.json`, chain/standard updated to Solana / Metaplex Core |
| `rig` mapping | `Alley_Kingz/research/GAME_VISION.md` (the 12 cars) -> `ROSTER_CANON.md` Section 4 dog-to-rig table |
| faction + Mythic + rarity canon | `Alley_Kingz/ecosystem/ROSTER_CANON.md` (Sections 1-3, 9) |
| rig art language + Mythic confirmation | `Alley_Kingz/ecosystem/SEEDANCE_BATTLE_KIT.md` (Mythics $BCARDD/Jagged/Rosco/Crown Foxhound + Stonejaw Legendary verified) |

---

## 3. KILL-LIST (files now superseded by this directory)

These were the divergent / duplicate lineages. Each is retired in favor of `ecosystem/data/`.

| File (exact path) | Recommendation | Why |
|---|---|---|
| `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/cards.json` | **LEAVE AS ARCHIVE** (was the canon home; now superseded by this copy) | Original source. Keep read-only as the historical origin; readers should repoint to `ecosystem/data/cards.json`. |
| `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/decks.json` | LEAVE AS ARCHIVE | Same. Superseded by `ecosystem/data/decks.json`. |
| `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/ability_params.json` | LEAVE AS ARCHIVE | Same. Superseded by `ecosystem/data/ability_params.json`. |
| `01_BUSINESSES/BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/cards.json` | **RETIRE AS SOURCE** (generated mirror only; never hand-edit) | Byte-identical to canon (`cmp` verified 2026-06-03). Keep the Unity folder, but a build step copies canon into it so it can never drift. |
| `01_BUSINESSES/BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/decks.json` | RETIRE AS SOURCE (generated mirror) | Byte-identical duplicate (`cmp` verified). |
| `01_BUSINESSES/BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/ability_params.json` | RETIRE AS SOURCE (generated mirror) | Byte-identical duplicate (`cmp` verified). |
| `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/App_Files/GameData.json` (14 KB) | **ARCHIVE** (memory-pipeline pass, then `08_BACKUPS/archived_prototypes/alley_kingz_human_crew_draft/`) | A THIRD, conflicting roster: 19 HUMAN-crew cards, $BCARDD as a human-hybrid Legendary. Pre-dog-canon draft. Contradicts dogs-are-IP. |
| `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/Alley_Kingz/ArenaAdvance/Assets/Resources/GameData.Json` (15 KB) | **ARCHIVE** (same pipeline pass) | Near-duplicate of the App_Files human-crew draft (minor description drift). Same retired human-crew lineage. |

**Disposition rule (Comms Doctrine -- no deletion without a memory pass):** the two `GameData.json` human-crew drafts go through `memory_pipeline.ingest_before_delete()` before moving to `08_BACKUPS/archived_prototypes/alley_kingz_human_crew_draft/`. The Unity `Resources/` JSONs are NOT deleted; they are flagged "generated, do not hand-edit" and a build step copies this canon into them.

---

## 4. THE .SOL CONTRACTS ARE REFERENCE-ONLY

The chain is locked to **Solana / Metaplex Core**. The EVM Solidity contracts under
`01_BUSINESSES/Everlight_Ventures/Alley_Kingz/blockchain/contracts/` are an earlier Ethereum-era design and are now **reference-only -- not the deployment target**:

- `AlleyKingzCards.sol`, `AlleyKingzDogs.sol`, `AlleyKingzMarketplace.sol`
- `BCRDIToken.sol`, `BcrdiGameVault.sol`, `BcrdiStaking.sol`

They are kept for economic-design reference (token, staking, vault, marketplace logic) but the live mint, the NFT standard, and the `$BCARDD` token all live on Solana. `nft_metadata_template.json` and every card's `nft` block declare `chain: "solana"` / `standard: "metaplex-core"`.

---

## 5. NEXT STEPS (recommended, not yet done)

1. Repoint Unity build + any game/web reader to load from `ecosystem/data/` (this directory) instead of the OnyxPOS path.
2. Add a build step that copies canon -> Unity `Resources/` so the mirror cannot drift.
3. Run the memory-pipeline pass + archive the two `GameData.json` human-crew drafts.
4. ART_BIBLE: add the Mythic frame row (Crown Gold holo + animated crown sigil + rainbow holo edge).

*Built by the canon-merge 2026-06-03. Pairs with `ROSTER_CANON.md`, `SEEDANCE_BATTLE_KIT.md`, `MASTER_BUILD_PLAN.md`, and `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`.*
