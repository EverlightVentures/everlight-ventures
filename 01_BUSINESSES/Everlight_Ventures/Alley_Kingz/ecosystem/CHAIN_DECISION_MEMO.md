# CHAIN DECISION MEMO -- Alley Kingz NFTs x $BCARDD
**Date:** 2026-06-02 · **Author:** Chain Architect (Hive fork) · **Status:** RECOMMENDED path, pre-build, for operator sign-off
**Resolves:** Master Ecosystem Plan "DECISION A -- Chain unification" (the gate that currently blocks all NFT work)
**Pairs with:** `BCARDI_Crypto/00_Core/BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`, `Alley_Kingz/MASTER_ECOSYSTEM_PLAN_2026-06-02.md`

---

## 0. TL;DR (the one-line decision)

**Go Solana-native. One Phantom wallet holds the $BCARDD coin AND every Alley Kingz NFT.** Mint the 48 playable stat-cards as **Metaplex Core** assets with the **Attribute Plugin** holding HP/damage/ability ON-CHAIN. Mint the 10,000 cosmetic Genesis dogs as **compressed NFTs (Bubblegum V2)** for fractions of a cent. Keep all six `.sol` files as battle-tested reference logic; port their RULES, not their bytecode. $BCARDD (the pump.fun SPL token) is the marketplace currency.

Do NOT keep the EVM contracts live and do NOT build a bridge. The EVM token they reference is a dead, superseded chain (see section 2).

---

## 1. The question, precisely

The NFTs are not pictures -- they ARE playable cards. Owning the $BCARDD NFT = owning the Mythic card with on-chain HP 2600 / damage 160 / ability "Crownbreaker". The marketplace currency must be $BCARDD. So the chain has to do four things at once:

1. **One wallet** for coin + NFTs (mass-psychology clean, hands-off-founder simple) -- Phantom.
2. **Cheap mints** at thousands-of-cards scale.
3. **On-chain stats** a game/marketplace program can actually read and gate on, not just JSON a website trusts.
4. **A clean port** of the existing Solidity logic (cards, dogs, marketplace, vault, staking) without rebuilding the design.

The conflict: **the coin is Solana, the existing NFT contracts are EVM Solidity.** A split ecosystem = two wallets, two explorers, two liquidity stories, double the maintenance, and a confused holder base. That is the exact opposite of "one dog, one currency, one aesthetic, one arcade."

---

## 2. The fact that makes this easy: the EVM token is ALREADY dead

This is the load-bearing discovery. People assume "EVM contracts exist, so we have an EVM ecosystem to protect." We do not.

- `BCRDIToken.sol` line 11 states it plainly: *"$BCRDI - The native token for Alley Kingz on **Zilliqa EVM**"* with a **ZIL** presale and **ZilSwap** BCRDI/ZIL liquidity.
- The Solana relaunch spec (section 2, "Decisions locked") **supersedes the stalled 2025 Cronos launch** (legacy contract `0xc7AdBbA52EA64B008a7e5d7666876628Dc391d69`, "low/no liquidity -- kept as legacy, not revived").
- So the canonical coin is now **$BCARDD, an SPL token on Solana, launched via pump.fun.** There is no live EVM token with liquidity to bridge to. The EVM `BCRDIToken` is a paper contract that was never the winning launch.

Conclusion: there is **nothing on EVM worth preserving as live infrastructure.** The Solidity files are valuable as *design specs* (the economics, the burn loop, the vault halving, the marketplace fee math are all good and proven by audit-grade OpenZeppelin patterns), but the chain itself is a discarded branch. We are not abandoning a working system; we are choosing the one chain the money already lives on.

This kills "EVM + bridge" on the merits: you would be bridging to a token that does not exist, doubling attack surface (bridges are the #1 exploit target in crypto) to connect a live Solana coin to dead Zilliqa contracts. No.

---

## 3. Solana-native vs EVM+bridge -- the comparison

| Dimension | Solana-native (RECOMMENDED) | EVM + bridge (REJECTED) |
|---|---|---|
| Wallet | ONE Phantom: $BCARDD + all NFTs together | Phantom for coin, MetaMask for NFTs, a bridge UI between |
| Mint cost (stat-card) | ~0.0029-0.0037 SOL (~$0.70) via Core | Gas on Zilliqa/L2; token-metadata-equivalent cost + RPC |
| Mint cost (10k dogs) | ~$0.001 each via Bubblegum cNFT (~$10-100 for 10k) | ERC-721 mint gas x 10,000 = the expensive part of the .sol design |
| On-chain stats | Core Attribute Plugin: key-value pairs Solana programs read | ERC-1155 struct in storage (works, but wrong chain) |
| Marketplace currency | $BCARDD SPL token, native, same wallet | $BCARDD would have to be bridged to EVM to pay -- absurd |
| Attack surface | One chain, audited Metaplex programs | + a bridge (highest-risk component in crypto) |
| Holder story | "Buy the coin, hold the cards, all in Phantom" | "Buy on Solana, bridge to EVM to get your card" = churn |
| Founder ops load | Low (managed Metaplex programs, no contract to maintain) | High (deploy + maintain Solidity + bridge + relayer) |
| Tooling maturity 2026 | Core + Core Candy Machine + Bubblegum V2, all live | Mature, but irrelevant here |

There is no column where the bridge wins for THIS project. The only reason to keep EVM would be an existing EVM userbase/liquidity -- and section 2 proves there is none.

---

## 4. WHERE THE STATS LIVE (the technical crux)

The whole "NFT IS the card" promise rises or falls on this. Two Solana NFT roads, and they differ exactly on whether a program can read the stats:

### 4a. Metaplex Core + Attribute Plugin -- for the 48 playable cards
- Each Core asset is a **single on-chain account** (Core collapsed the old multi-account Token Metadata model into one, which is why it is ~80% cheaper).
- The **Attribute Plugin** stores **key-value string pairs directly on-chain**, inside the asset. Per Metaplex docs (updated 2026-01-31): *"perfect for game stats, traits, and any data that on-chain programs need to read... readable by Solana programs and indexed by DAS."*
- **Mutable by the update authority** (not the owner) -- so the game treasury can patch a stat in a balance update, but a player cannot edit their own card to cheat. Exactly the trust model a competitive card game needs.
- Caveat: **values are strings** -- store `{key:"hp", value:"2600"}`, `{key:"damage", value:"160"}`, parse to int in the game/program. Trivial.

This is the answer to "on-chain HP/damage/ability." $BCARDD's HP 2600, damage 160, Crownbreaker ability, queen_target=true all live in the Attribute Plugin, readable by the marketplace program and the game server alike.

### 4b. Hybrid: on-chain stats vs off-chain metadata (the right split)
Do NOT put everything on-chain (wasteful) and do NOT put stats off-chain (defeats the promise). Split by what needs to be trustless:

- **ON-CHAIN (Attribute Plugin):** the gameplay-load-bearing, anti-cheat stats -- `hp`, `damage`, `attack_speed`, `move_speed`, `range`, `cost`, `rarity`, `ability_id`, `queen_target`. These gate matches and pricing; they must be tamper-evident.
- **OFF-CHAIN (JSON metadata, IPFS/Arweave):** the heavy + cosmetic fields -- the `image`, the Seedance `animation_url` battle video, `description`, `external_url`, the long ability flavor text. These are exactly the fields already in `nft_metadata_template.json`. They are big and do not need consensus.
- The existing `nft_metadata_template.json` is already the correct OFF-CHAIN shape (image + animation_url + attributes). We keep it as the off-chain JSON and additionally mirror the gameplay-critical attributes into the on-chain Attribute Plugin. Best of both: cheap storage for video, trustless storage for stats.

### 4c. Compressed NFTs (Bubblegum V2) -- for the 10,000 cosmetic dogs
- Stats are NOT stored in a readable per-asset account; only a **Merkle hash** is on-chain, full data indexed off-chain via the Aura/DAS network. A Solana program cannot cheaply dereference an individual cNFT's traits at runtime.
- Therefore cNFTs are WRONG for the playable stat-cards (no trustless on-chain stat to gate on) but PERFECT for the `AlleyKingzDogs.sol` use case: 10,000 Genesis cosmetic companion dogs, airdropped, cosmetic-only buffs, "NOT pay-to-win" (the contract's own words). Cost ~$0.001/mint -> the entire 10k Genesis drop costs ~$10-100 total.
- Bubblegum V2 (2026) now lives inside Core Collections, so cNFTs can enforce royalties (ProgramDenyList) and be made soulbound. They share the collection with the Core cards -- one collection, two asset classes.

---

## 5. HOW THE EXISTING `.sol` LOGIC PORTS (1:1 map)

The Solidity is good design. We port the RULES to Solana primitives. Six files, six destinations:

| EVM contract (reference) | Its job | Solana-native destination |
|---|---|---|
| `AlleyKingzCards.sol` (ERC-1155, stat structs, rarity, genesis-lock, pack mint, burn-for-upgrade) | The 48 playable stat-cards | **Metaplex Core collection + Attribute Plugin** for stats. Pack opening + genesis-lock + per-card max-supply become **Core Candy Machine guards** (allowlist, supply caps, start dates). Burn-for-upgrade = Core asset burn instruction. |
| `AlleyKingzDogs.sol` (ERC-721, 10k Genesis cap, breeds, cosmetic traits, airdrop batch) | 10k cosmetic companion dogs | **Bubblegum V2 compressed NFTs** in the same Core collection. Airdrop batch = cNFT mint loop (the cheap path the design wanted but EVM gas killed). |
| `AlleyKingzMarketplace.sol` (escrow listings, 2.5% fee burned, 2.5% royalty, $BCRDI payment) | P2P card/dog trading in $BCARDD | A small **Anchor program** (escrow + fee-burn) OR list on an existing Solana marketplace (Tensor/Magic Eden) that already supports Core + SPL-token payment and royalty enforcement. FREE-FIRST: try the existing marketplaces before writing the Anchor escrow. |
| `BcrdiGameVault.sol` (P2E reward, arena scaling, season halving, daily cap, authorized game server) | Pays $BCARDD for battle wins | **Off-chain game server signs SPL-token transfers** from a treasury PDA / token account; the arena-multiplier + halving + daily-cap math ports verbatim into the server (or a thin Anchor program if trustless emission is wanted later). Per the BCARDI spec section 9: AI/server is off-chain, never holds keys to the founder bag. |
| `BcrdiStaking.sol` (staking rewards pool) | Stake $BCARDD for rewards | Solana staking program OR Streamflow/Jupiter Lock (already named in the BCARDI spec for the founder-bag vest). FREE-FIRST: reuse the lock tool already chosen for launch. |
| `BCRDIToken.sol` (ERC-20 on Zilliqa) | The token | **DELETE as live infra.** Replaced by the pump.fun SPL $BCARDD. Keep only the burn-loop + allocation math as economic reference. |

Net: of six contracts, **zero need to be deployed as Solidity.** One (the token) is fully replaced by pump.fun. Three (vault/staking/marketplace) become off-chain server logic or reuse existing Solana programs. Two (cards/dogs) map to managed Metaplex standards we configure, not code we write from scratch. This is dramatically LESS code to own than the EVM path -- which is the right outcome for a hands-off founder.

---

## 6. THE EXACT FREE / OPEN-SOURCE TOOLS (FREE-FIRST law applied)

All of these are free open-source SDKs/CLIs; the only on-chain cost is the mint rent itself (the per-mint numbers in section 3).

1. **Metaplex Umi + `@metaplex-foundation/mpl-core`** (open-source JS SDK) -- create the collection, mint Core assets, attach the Attribute Plugin with the card stats. FREE.
2. **`@metaplex-foundation/mpl-core-candy-machine`** (open-source) -- the fair-launch vending machine for the card set. 23+ composable guards: **SPL-token payment guard set to $BCARDD**, allowlist (coin-holder whitelist), start date, bot protection, per-mint supply caps (= the EVM maxSupply/genesis-lock). FREE.
3. **`@metaplex-foundation/mpl-bubblegum`** (open-source, V2) -- mint the 10k compressed Genesis dogs into the same collection. FREE SDK, ~$0.001/mint on-chain.
4. **Metaplex CLI** (`mplx`) -- scriptable mint/airdrop from the e5-mother box (NOT the phone proot -- npm install segfaults on the phone per HARD LAW; build/run mint scripts on e5-mother or AceMagician). FREE.
5. **Storage:** **Arweave via Irys** (formerly Bundlr, permanent, pennies) or **NFT.Storage/IPFS** (free tier) for the off-chain JSON + Seedance `animation_url` videos. The template already targets `ipfs://` CIDs. FREE tier first; Irys only if permanence matters more than the free IPFS pin.
6. **Marketplace:** list on **Tensor** and/or **Magic Eden** (free to list, they already support Core + SPL-token offers + royalty enforcement) BEFORE writing the custom Anchor escrow. Only build the Anchor marketplace if a $BCARDD-denominated, fee-burning custom market is a hard requirement the aggregators cannot meet.
7. **RPC:** Helius or QuickNode **free tier** (DAS API support for reading Core attributes + cNFTs) for the game server to read stats. FREE tier covers launch volume.
8. **Lock/vest (founder bag + any staking):** **Streamflow or Jupiter Lock** -- already named in the BCARDI relaunch spec section 5. Reuse, do not add a new tool.

**Only real spend:** the per-mint SOL rent (section 3 numbers -- trivial: ~$0.70/card x 48 = ~$34 for the whole playable set; ~$10-100 for 10k dogs) + Seedance video credits (already a separate, phased line item in the master plan) + the $BCARDD dev-buy (already planned). No new SaaS, no paid bridge, no contract-audit bill (Metaplex programs are already audited; we write almost no custom on-chain code).

---

## 7. THE PHANTOM "ONE WALLET" PAYOFF

With this path, the holder experience is the unified story the operator wants:
- Open Phantom. See **$BCARDD** (the coin) and your **Alley Kingz cards + dogs** in the same wallet, same app, same chain.
- Buy a card on Tensor/Magic Eden -> pay in **$BCARDD** -> the $BCARDD NFT lands in the same Phantom -> its **HP 2600 / Crownbreaker** is already on-chain and readable by the Arcade game the moment it arrives.
- Win a battle -> the vault server sends **$BCARDD** to that same Phantom.
- Same dog on the coin, the dealer video, and card #0001. One wallet threads all of it.

The EVM+bridge path breaks every one of those into a two-app, two-chain chore. The recommendation is not close.

---

## 8. MIGRATION APPROACH (no live EVM state to migrate -- it is a clean greenfield)

Because nothing shipped on EVM with real holders (section 2), there is no token/NFT migration burden -- this is a fresh Solana mint, not a chain-to-chain port of live assets. The "migration" is purely getting the design onto Solana:

1. **Lock this memo** as Decision A resolved (operator sign-off). Mark the `.sol` files `// REFERENCE ONLY -- superseded by Solana-native, see CHAIN_DECISION_MEMO.md` so no one redeploys them.
2. **Canon the roster first** (Master Plan Phase 2): merge the 48-card `cards.json` into the single source of truth. The on-chain Attribute Plugin reads from this canon -- it must be settled before minting or the stats are wrong on-chain forever (well, until an authority update, but mint it right).
3. **Create the Core collection** on e5-mother via Umi + mpl-core. One collection holds both the Core stat-cards and the Bubblegum dogs.
4. **Stat-card mint:** write the 48 cards' attributes (from canon `cards.json`) into the Attribute Plugin; off-chain JSON (image + Seedance animation_url) to Arweave/IPFS. Mythics first ($BCARDD #0001), matching the Seedance Mythic-first phasing already in the master plan.
5. **Candy Machine** with the $BCARDD SPL payment guard + coin-holder allowlist for the public card drop.
6. **Dog drop:** Bubblegum V2 cNFT airdrop of the 10k Genesis cosmetic dogs to early holders / blackjack players (ties to the BCARDI spec airdrop wave).
7. **Marketplace:** list on Tensor/Magic Eden in $BCARDD; defer the custom Anchor escrow unless a fee-burning $BCARDD-native market proves necessary.
8. **Game-server vault:** port the arena/halving/daily-cap math from `BcrdiGameVault.sol` into the off-chain server signing $BCARDD transfers. Keys never on the AI side (BCARDI spec section 9).
9. **Verify + log:** read back the on-chain attributes via DAS (Helius free tier) to PROVE stats are on-chain (receipt, not a claim), then log the decision to Blinko.

Sequence note: the coin ships first (it is closest and funds the rest), then the Mythic cards, per the master plan's "do not parallelize the spend."

---

## 9. RECOMMENDATION (one path, default chosen)

**Solana-native. Metaplex Core (Attribute Plugin) for the 48 playable stat-cards + Bubblegum V2 cNFTs for the 10k cosmetic dogs, one Phantom wallet, $BCARDD SPL token as the marketplace + reward currency, existing Solana marketplaces before any custom Anchor code, all heavy mint scripts run on e5-mother not the phone.**

The `.sol` files stay as design reference and get a header banner marking them superseded. There is no bridge. There is one chain, one wallet, one currency, one aesthetic -- which is exactly the north star.

This is the default. Flipping it (keeping EVM + bridge) would re-introduce a second chain to connect to a token that does not exist, double the wallet/attack/maintenance surface, and break the "all in Phantom" holder story -- with no offsetting benefit, because there is no live EVM userbase to preserve.

---

## 10. OPEN ITEMS FOR THE OPERATOR (surfaced, with a recommended default each)

1. **Custom $BCARDD marketplace vs aggregators?** Default: launch on Tensor/Magic Eden in $BCARDD (free, fast); build the fee-burning Anchor escrow only if a $BCARDD-denominated deflationary market becomes a marketing requirement. (FREE-FIRST.)
2. **Attribute mutability policy.** Default: update authority = a treasury multisig/PDA the game controls, so balance patches are possible but no single hot key can rewrite every card. Decide who holds it before mint.
3. **Stat-card supply model.** EVM design had genesis-lock + per-card max-supply. Default: Mythics very scarce ($BCARDD #0001 1-of-1 or tiny), commons higher supply via Candy Machine guards -- confirm the exact ladder during Phase 2 canon.
4. **Storage permanence.** Default: free IPFS pin first; upgrade Mythic videos to Arweave/Irys (permanent, pennies) since they are the hero assets. Operator spend call, but it is cents.

---

*Compiled 2026-06-02 from the six Alley Kingz `.sol` contracts, `nft_metadata_template.json`, the 48-card `cards.json` (4 Mythic / 1 Legendary / 9 Epic / 20 Rare / 14 Common), the BCARDI Solana relaunch spec, and live 2026 Metaplex tooling/cost confirmation. Resolves Master Ecosystem Plan Decision A. Next: operator sign-off, then Phase 2 canon merge, then the Core collection mint on e5-mother.*

## Sources (live 2026 confirmation)
- Metaplex Core standard + cost (~0.0029-0.0037 SOL/mint vs 0.022 Token Metadata): https://www.metaplex.com/docs/smart-contracts/core , https://nftplazas.com/solana-nft-protocol/
- Core Attribute Plugin (on-chain key-value game stats, mutable by update authority, readable by programs, docs updated 2026-01-31): https://developers.metaplex.com/core/plugins/attribute , https://www.metaplex.com/docs/smart-contracts/core/plugins/attribute
- Core Candy Machine (thousands-scale fair launch, 23+ guards, SPL-token/NFT payment): https://www.metaplex.com/docs/smart-contracts/core-candy-machine , https://developers.metaplex.com/core-candy-machine
- Bubblegum V2 compressed NFTs (~$0.001/mint, Merkle-hash on-chain + Aura/DAS off-chain, now inside Core Collections, royalty + soulbound support): https://developers.metaplex.com/smart-contracts/bubblegum-v2 , https://www.helius.dev/blog/solana-nft-compression
