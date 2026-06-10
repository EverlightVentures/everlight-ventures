# ALLEY KINGZ x $BCARDD -- REUSE MANIFEST
**Date:** 2026-06-02 | **Author:** Free-First Resource Scout (Hive fork) | **Status:** Audit complete, ready for operator review
**Pairs with:** `MASTER_ECOSYSTEM_PLAN_2026-06-02.md` (one dir up) and `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`

> **Purpose:** A line-by-line ledger of what is ALREADY built (do NOT rebuild) versus the exact free/open-source tools to pull for the gaps, versus the only real cash spend. FREE-FIRST law applied: existing infra -> self-host open-source -> free tiers -> build, before any paid path. Spend is labeled in ONE section so it cannot hide.

---

## 0. HEADLINE FINDINGS (read these first)

1. **The repo catalog has ZERO game/blockchain entries.** `open_source_repo_stack.yaml` (627 lines, 26 repos) is purely AI/agent/RAG infra (CrewAI, FAISS, LangChain, Qdrant, Ollama, whisper, Playwright, Firecrawl). It contributes NOTHING directly to Alley Kingz -- the only binding rule that touches us is "keep xlm_bot/main.py untouched" (irrelevant here) and the general "adopt in phases / sidecar / feature venv" install policy. **The Solana NFT + game-engine tools below must be pulled fresh from upstream open-source; the catalog cannot supply them.** This is a gap, not a blocker.
2. **The card canon is 48 cards, NOT 50.** Master plan says 50; the actual `cards.json` (both copies, byte-identical card count) has exactly **48 cards: 4 factions of 12 each.** Rarity split: 4 Mythic, 1 Legendary, 9 Epic, 20 Rare, 14 Common. Use 48 in all budget math.
3. **Chain split is real and confirmed at the code level.** The coin is **Solana/pump.fun/Phantom** (per `BCARDI_SOLANA_RELAUNCH_SPEC`). The NFT contracts are **EVM/Solidity** (ERC-1155, OpenZeppelin 5.6.1, hardhat targeting **Zilliqa EVM** testnet/mainnet + local). Decision A in the master plan (go Solana-native for NFTs) is the right call AND the existing `.sol` is wired to Zilliqa, not even Ethereum -- so there is no Ethereum mainnet sunk cost to abandon. Keep `.sol` as reference logic only.
4. **The `verify-arcade-purchase` Supabase function does NOT exist yet.** Master plan section 2 lists it as built; the live functions dir `vantaris/supabase/functions/` contains only `notify-lead`. The arcade PAGE routes exist (`/arcade`, `/alley-kingz`, `/play/blackjack`, `/vantaris/blackjack`) but purchase verification is a GAP to build, not a reuse.

---

## 1. ALREADY BUILT -- DO NOT REBUILD

Every path below was verified to exist on 2026-06-02. Treat these as canon inputs; rebuilding any of them is waste.

### 1a. Game design + data canon
| Asset | Verified path | What it is | Reuse rule |
|---|---|---|---|
| **Card roster (DOG canon)** | `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/cards.json` | **48 cards**, 4 factions x 12 (Boneguard Crew, Zoomie Syndicate, Leashbreak Tactix, K9 Circuitry). Full stats (hp/damage/attack_speed/move_speed/range/cost), abilities w/ cooldowns. **$BCARDD = card #1, Mythic, HP 2600, "Crownbreaker", queen_target true.** | THE source of truth for cards. Pick this as canon; collapse the duplicate. |
| **BCARDI Unity card set (duplicate)** | `01_BUSINESSES/BCARDI_Crypto/dell_unity_setup_dec2025/Assets/BCARDI/Resources/{cards,decks,ability_params}.json` | Same 48 cards, already wired into a Unity card set + `decks.json` + `ability_params.json`. | Reuse the `decks.json` + `ability_params.json` (the OnyxPOS copy lacks these). Merge into one canon, do NOT keep two live copies (Phase 2 of master plan). |
| **NFT metadata template** | `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/nft_metadata_template.json` | $BCARDD #0001 metadata w/ `image` + `animation_url` (video-NFT ready) + 15 on-chain stat attributes matching cards.json. Already uses `ipfs://` + `symbol: BCARDI`. | Reuse verbatim as the Metaplex JSON schema. Stats already map 1:1 to cards.json. Just swap EVM assumptions for Metaplex Token Metadata fields. |
| **Game vision (CAR direction)** | `Alley_Kingz/research/GAME_VISION.md` | 12-car roster, Chop Shop breeding, monetization stack. | Fold the 12 cars in as the *vehicles the dogs pilot* (master plan Decision B), not separate characters. |

### 1b. Playable builds + engine code
| Asset | Verified path | What it is | Reuse rule |
|---|---|---|---|
| **HTML prototypes v4-v8** | `Alley_Kingz/Alley_Kingz/prototype/game_v{4,5,6,7,8}.html` | Playable browser builds. **v8 = 213 KB, Three.js / WebGL canvas** (latest). Plus `combat_upgrades.js` (38 KB), `graffiti_system.js` (32 KB), `art_prompts.md`, `build_v5.py`. | **game_v8 is the web-Arcade starting point** (master plan Decision 4 = web-first). Do not start a new web build. Three.js is already the render layer -- matches blackjack's Three.js, so the arcade is visually unified. |
| **Unity project "ArenaAdvance"** | `Alley_Kingz/Alley_Kingz/ArenaAdvance/Assets/` (+ build copy at `Alley_Kingz_Build/ArenaAdvance/`) | Full Unity C# project: Scripts/{Core,Gameplay,Economy,Contracts,AI,UI,Managers,Data,Progression,Audio,Battle,Cards,Services,ScriptableObjects}, a `BattleDebug.unity` scene, `Resources/GameData.Json`. Key files: `BattleManager.cs`, `BattleSystem.cs`, `UnitBehaviour.cs`, `HQVanSystem.cs`, `Matchmaking.cs`, `EconomyManager.cs`, `CardDefinition.cs`, `DeckBuilderSystem.cs`, `AuthManager.cs`. | THE mobile/3D target (master plan Phase 8 "metaverse later"). Do NOT rewrite the battle loop -- `BattleSystem.cs` + `UnitBehaviour.cs` + `HQVanSystem.cs` are the lane-battler core. Reuse for the eventual app-store + metaverse layer. |
| **Loose C# scripts (App_Files)** | `Alley_Kingz/App_Files/*.cs` | 14 standalone C# files (BattleManager, BattleSystems, Economymanager, Carddefinition, Gameenums, Matchmaking, contractadvisor, etc.) + `GameData.json`. | These are the SAME scripts as ArenaAdvance/Assets/Scripts (loose backup copy). Treat ArenaAdvance as canonical; App_Files is an archive. Do not maintain both. |

### 1c. Art + production doctrine
| Asset | Verified path | What it is | Reuse rule |
|---|---|---|---|
| **Art Bible v1.0** | `Alley_Kingz/ART_BIBLE.md` (7 KB) | Locked palette, rarity tiers, hyper-real SOP. | The visual law. Every Seedance prompt cites it. Do not redefine the palette. |
| **Prompt Bible** | `Alley_Kingz/PROMPT_BIBLE.md` (13 KB) | Prompt spine for the gen pipeline. | Reuse for Seedance prompts; extend with the Twisted-Metal-rig language, do not rewrite. |
| **Visual AI Pipeline SOP** | `Alley_Kingz/VISUAL_AI_PIPELINE_SOP.md` (5.5 KB) | 6-stage gen -> Art Review Gate -> perf-check -> repo -> content_pack pipeline. | MANDATORY gate for all generated art. No AI slop ships unreviewed. |
| **content_pack.json** | `Alley_Kingz/content_pack.json` | v2.0 asset registry. Locked palette (Crown Gold `#D4AF37`, Midnight Deep `#0D0D1A`, Neon Cyan `#00F5FF`, Brick Warm `#C1440E`, Asphalt Grey `#4A4A55`), mobile spec (2K texture / 45k poly / ASTC, Snapdragon 665 floor @ 60FPS), 6-stage review_statuses, asset_types. **`assets: []` is empty -- this is the ledger the Seedance output fills.** | Reuse as the asset manifest. Every approved Seedance clip gets a row here. The `#D4AF37` Crown Gold ties to the Everlight brand AND the $BCARDD coin art. |
| **Seedance precedent (Blackjack)** | `Everlight_Gaming/Blackjack/SEEDANCE_ART_BRIEF.md` | PROVEN cost model: images 10-20 credits, **videos 300 credits** (Seedance Video 1.0 Pro, 3-4s, loop-ready). Full credit-tiering strategy + prompt best-practices + Three.js integration guide. | THE template for the Alley Kingz Seedance batch. Copy the tier structure; the dealer-video workflow already shipped, so the rig-video workflow is a known quantity. |
| **Avatar prompt bank** | `Everlight_Foundations/SEEDANCE_AVATAR_PROMPTS.md` | Additional proven Seedance prompts. | Mine for reusable cyberpunk/neon prompt fragments. |

### 1d. Specs + economy
| Asset | Verified path | Reuse rule |
|---|---|---|
| Product + data + pack specs | `Alley_Kingz/spec/PRD_V2.md`, `05_DATA_MODEL.md`, `PACK_RIP_OUTCOME_MODEL.md` | The product law + pack economy. Reuse the pack-rip outcome model for NFT pack mints. |
| Monetization UX | `Alley_Kingz/MONETIZATION_UX_REWRITE.md` (22 KB), `ONLINE_STORE_SPEC.md`, `MASTER_ECOSYSTEM_PLAN.md` section 4 | The chips/utility/buyback-burn loop. $BCARDD = the chip. |

### 1e. Blockchain (reference logic, not the deploy target)
| Asset | Verified path | What it is | Reuse rule |
|---|---|---|---|
| **EVM NFT + token contracts** | `Alley_Kingz/blockchain/contracts/{AlleyKingzCards,AlleyKingzDogs,AlleyKingzMarketplace,BcrdiGameVault,BcrdiStaking,BCRDIToken}.sol` | 6 Solidity contracts. `AlleyKingzCards.sol` = ERC-1155, EIP-2981 2.5% royalty, CardMeta struct (name/rarity/cardType/elixirCost/breed/maxSupply), authorized-minter pattern, genesis lock. Plus a marketplace, a staking, a game-vault, and a BCRDI ERC-20. OpenZeppelin 5.6.1, solc 0.8.27, hardhat. **hardhat.config targets Zilliqa EVM testnet(33101)/mainnet(32769) + local(31337) -- NOT Ethereum mainnet, so no costly migration to abandon.** | **KEEP AS REFERENCE LOGIC ONLY** (master plan Decision A). The royalty %, the rarity enum (0=Common..4=Mythic), the authorized-minter + genesis-lock + pack-batch-mint patterns are battle-tested business rules to PORT to Solana, not to redeploy. Do NOT deploy these to mainnet. |

### 1f. Arcade + site (Vantaris)
| Asset | Verified path | What it is | Reuse rule |
|---|---|---|---|
| **Arcade hub pages** | `06_DEVELOPMENT/vantaris/src/app/{arcade,alley-kingz,play/blackjack,vantaris/blackjack}/` | Next.js arcade hub + an alley-kingz route + two blackjack routes already exist. | Mount the Alley Kingz web build (from game_v8) here. Do not scaffold a new arcade. |
| **Site theme** | `06_DEVELOPMENT/vantaris/` (everlightventures.io, Cloudflare Pages, Three.js/framer-motion/gsap, Supabase back, Stripe live) | The live public site + brand theme. | Reuse the gold theme + Three.js layer for arcade visual unity. |

### 1g. $BCARDD launch kit (parent session, do not rebuild)
| Asset | Verified path | Reuse rule |
|---|---|---|
| Solana launch spec | `BCARDI_Crypto/00_Core/BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md` + `BCARDI_LAUNCH_PLAN_2026-06-02.md` | pump.fun fair launch, 1B fixed supply, Phantom wallet (seed in Proton Pass), ~9% dev buy, creator-fee -> buyback-burn. THE coin plan. |
| Community + GTM kit | `BCARDI_Crypto/02_Community/{X_LAUNCH_KIT,COPY_PACK,DISCORD_SETUP,AUTOMATION_GAMEPLAN}.md` | X autopilot + copy + Discord already drafted. Reuse for NFT/arcade cross-promo. |
| Coin art + dealer video | `BCARDI_Crypto/01_Media/` + the shipped Seedance blackjack dealer video | The mascot art is done; the dealer IS $BCARDD. One-dog through-line already proven on screen. |

---

## 2. THE GAPS -- EXACT FREE / OPEN-SOURCE TOOLS TO PULL

None of these are in `open_source_repo_stack.yaml`. They are pulled fresh from upstream. All are free/open-source; the only cash is in Section 3.

### 2a. Solana NFT stack (FREE -- this is the Decision-A enabler)
Go Solana-native so the NFT lives in the same Phantom wallet as the $BCARDD coin. Tooling, in priority order:

| Tool | Repo / source | What it does for us | Cost |
|---|---|---|---|
| **Metaplex Core** | `metaplex-foundation/mpl-core` (github.com/metaplex-foundation/mpl-core) | The current Solana NFT standard -- single-account NFTs, **~85% cheaper to mint than legacy Token Metadata**, native plugins for royalties + freeze + attributes. **Use this for the 48 flagship cards** (hero, tradeable, on-chain stats). The `nft_metadata_template.json` attributes map straight into Core's attribute plugin. | FREE lib; pay only Solana rent (cents). |
| **Bubblegum v2 (compressed NFTs)** | `metaplex-foundation/mpl-bubblegum` | **State-compressed NFTs -- mint thousands for a few dollars total.** Use for the high-volume tail: pack-rip commons/rares, airdrop drops, edition copies. The 14 Common + 20 Rare = 34 cards' bulk supply goes here. | FREE lib; ~$0.0001/mint via Merkle-tree compression. |
| **Sugar (Candy Machine CLI)** | `metaplex-foundation/sugar` + Candy Machine v3 | The mint-launch machine: config a collection, set the mint price (in SOL or $BCARDD-via-token-gate), public/whitelist phases, reveal. This replaces the EVM "PackOpener/authorized-minter" pattern from `AlleyKingzCards.sol`. | FREE CLI. |
| **Umi** | `metaplex-foundation/umi` | The JS framework all the above run on (one client, modular signers/RPC). Build the mint scripts in Umi instead of porting hardhat/ethers. | FREE. |
| **Phantom + Solana wallet-adapter** | `solana-labs/wallet-adapter` (`@solana/wallet-adapter-react`) | Wire the arcade's Next.js front end to Phantom -- the SAME wallet that holds $BCARDD. One connect button = coin + cards + chips. | FREE. |
| **Helius (RPC + DAS API)** | helius.dev free tier | RPC + the Digital Asset Standard read API to display owned NFTs/cNFTs in the arcade. Free tier covers launch volume. | FREE tier (free-first; only upgrade if volume forces it -- label as spend then). |
| **Irys / Arweave (or IPFS via web3.storage)** | `irys-xyz/js-sdk` or web3.storage free tier | Permanent storage for the Seedance `animation_url` MP4s + metadata JSON. Irys = pay-once permanent (cents per clip); web3.storage IPFS free tier is the $0 path for launch. | web3.storage FREE tier first; Irys is cents-scale if permanence is required. |

**Port map (EVM -> Solana), so the reference logic is not lost:**
- `AlleyKingzCards.sol` rarity enum (0..4) -> Metaplex Core attribute `Rarity` (already in metadata template).
- EIP-2981 2.5% royalty -> Core royalties plugin (set basis points = 250).
- authorized-minter + genesis-lock -> Sugar/Candy Machine mint authority + collection freeze.
- `AlleyKingzMarketplace.sol` -> use an existing Solana marketplace (Tensor/Magic Eden list-for-free) instead of deploying a custom one; only build custom if $BCARDD-denominated trades are required.
- `BCRDIToken.sol` ERC-20 -> already superseded by the pump.fun SPL token (the coin). Drop the Solidity token entirely.

### 2b. Lane-battler / Clash-Royale reference engine (FREE)
No Clash-Royale-clone repo exists in our catalog. The web build does NOT need one -- **game_v8 already has the lane-battler running in Three.js.** For the gaps:

| Need | Free tool | Note |
|---|---|---|
| Web client (already have) | **game_v8.html (Three.js)** | Reuse. Do not adopt a new engine for web. |
| If a real-time multiplayer server is needed | **Nakama** (`heroiclabs/nakama`, Apache-2.0, self-host) OR **Colyseus** (`colyseus/colyseus`, MIT, Node) | Self-host on e5-mother. Nakama = batteries-included matchmaking/leaderboards; Colyseus = lighter room-based. Pick Colyseus if staying in the Node/Three.js web stack. Matches existing `Matchmaking.cs` concepts. |
| Mobile/3D (already have) | **Unity ArenaAdvance** | Reuse the C# battle loop. No new engine. |
| Open lane-battler to study (optional) | **`OpenClonk` / Godot Clash-style samples** | Reference only; we are NOT forking a game. Our battle logic already exists in two implementations (Unity + game_v8). |

**Recommendation:** do NOT pull a new battler engine. We have two working implementations. Add Colyseus ONLY when PvP-realtime is on the roadmap (not in the launch path).

### 2c. Free render rails (phone proot CANNOT do this -- HARD LAW)
The phone proot cannot run ffmpeg-heavy pipelines, Unity builds, or `npm install` (SIGSEGV, per memory). All heavy media routes off-phone:

| Job | Where it runs (free, existing infra) | How |
|---|---|---|
| Seedance clip post-processing (trim, loop, transcode to web MP4/H.264 + WebM) | **e5-mother** (Ampere ARM, tailnet) via `ssh e5-mother` | ffmpeg on e5. The workspace is symlinked (`/mnt/sdcard/AA_MY_DRIVE -> /home/ubuntu/AA_MY_DRIVE`) so canonical paths Just Work. |
| HTML-card -> MP4 promo clips | **e5-mother** via the `everlight_hyperframes` skill | Already built; renders branded HTML -> MP4 on e5, never the phone. |
| Unity build (Android APK / WebGL export) | **AceMagician PC** (Arch, tailnet 100.93.253.49) or a cloud Unity runner | Phone cannot build Unity. Route the ArenaAdvance build to the PC. |
| NFT image/metadata batch generation + IPFS pin | **e5-mother** (Node/Umi scripts) | Build mint scripts on e5 (phone cannot npm install). Serve/run over tailnet. |
| Arcade Next.js build | **e5-mother** (`next build`), then serve/deploy | Per the proot-cannot-npm HARD LAW: build remote, deploy artifact to Cloudflare Pages. |

### 2d. Already-free infra to lean on (no new tooling)
- **Cloudflare Pages** -- arcade + site hosting (already live for everlightventures.io). $0.
- **Supabase** -- arcade identity + purchase ledger + leaderboards (already the SOT). $0 on current tier. NOTE: build the missing `verify-arcade-purchase` edge function here (Gap from Section 0).
- **Solana devnet** -- test every mint for free before mainnet. $0.
- **Tensor / Magic Eden** -- list NFTs for trade with no custom marketplace contract. $0 to list.

---

## 3. THE ONLY REAL CASH SPEND (clearly labeled)

FREE-FIRST law: everything above is $0 or cents-scale rent. The genuine spend is exactly two line items. Confirm balances BEFORE committing (free-first law on Seedance credits).

| # | Spend | Amount | What it buys | Free-first status |
|---|---|---|---|---|
| 1 | **Seedance video credits** | ~300 credits / 3-4s clip (PROVEN rate from the Blackjack brief). **Batch 1 = 4 Mythic hero videos = ~1,200 credits.** Full 48-card set ~14,400 credits (do NOT bulk-buy). | The `animation_url` battle clips: Twisted-Metal dog-rig carnage per card. Phase it: 4 Mythics first (hype trailer + NFT preview), then the 1 Legendary + 9 Epics, then the 20 Rare + 14 Common as shorter/batch clips. | NO free substitute for the hero cinematic quality. Image-only fallback (FLUX/SDXL ~10-20 credits) exists for the long tail to cut spend. **Confirm credit balance + per-clip cost before each batch.** |
| 2 | **$BCARDD dev buy** | ~9% of supply at launch-floor (per the Solana relaunch spec) + ~$2 pump.fun deploy + a little SOL for gas. | The founder bag + the coin itself + Solana rent for NFT mints (cents). | Already planned in the parent session; this manifest does not change it. The buy is an investment, not a tool cost. |

**Everything else = $0:** Metaplex Core/Bubblegum/Sugar/Umi (free libs), Phantom + wallet-adapter (free), Helius/web3.storage (free tiers), Cloudflare Pages + Supabase (existing), e5-mother + AceMagician render (existing infra), Colyseus/Nakama (self-host, only if PvP-realtime is scoped), Tensor/Magic Eden listing (free).

---

## 4. ONE-PAGE REUSE DECISION (the default recommendation)

For a hands-off operator who wants ONE intertwined ecosystem:

1. **Canon:** OnyxPOS `cards.json` (48 cards) + the BCARDI Unity `decks.json`/`ability_params.json` = the single merged data layer. Kill the third copy.
2. **Chain:** Solana-native NFTs via **Metaplex Core (flagship 48) + Bubblegum (pack tail) + Sugar (mint launch)**, same Phantom as $BCARDD. `.sol` contracts kept as reference logic, never redeployed.
3. **Web game:** ship **game_v8 (Three.js)** inside `vantaris/src/app/arcade`, sharing the Phantom wallet + $BCARDD chips. Build the missing `verify-arcade-purchase` Supabase function.
4. **Art:** Seedance Mythic-first (4 clips, ~1,200 credits) through the existing Visual AI Pipeline SOP + Art Review Gate; log every approved clip into `content_pack.json`.
5. **Render:** e5-mother for ffmpeg/IPFS/Node builds; AceMagician for Unity; NEVER the phone.
6. **Mobile/metaverse:** Unity ArenaAdvance is the long-term target, untouched until the web build proves the loop.
7. **Spend:** only Seedance credits (phased) + the already-planned $BCARDD dev buy. Everything else free.

---

## 5. OPEN GAPS TO FLAG FOR THE OPERATOR
- `verify-arcade-purchase` edge function is referenced as "built" but is NOT in `vantaris/supabase/functions/` (only `notify-lead` is). Must be built before paid arcade flows.
- Master plan says "50 cards"; canon is **48**. Reconcile the number in the master plan + any marketing copy.
- Three card-data copies exist (OnyxPOS, BCARDI Unity, ArenaAdvance GameData). Pick ONE canon path (recommend OnyxPOS `cards.json` + BCARDI `decks.json`/`ability_params.json`) before any mint, or the game fragments.
- Decision A (Solana-native NFT) is recommended and code-confirmed safe (EVM contracts target Zilliqa, not Ethereum mainnet -- nothing costly to abandon), but it is still an operator sign-off, not done.
- Solana NFT tooling is NOT in the repo catalog; adding the Metaplex stack is net-new (free, but a fresh dependency -- follow the catalog's "feature venv / sidecar, phased adopt" install policy).

---

*Compiled 2026-06-02 by the Free-First Resource Scout. All paths verified to exist. Repo catalog read in full (627 lines / 26 repos, no game or blockchain entries). Card counts, rarity tiers, factions, contract details, and chain targets pulled directly from the files, not assumed.*
