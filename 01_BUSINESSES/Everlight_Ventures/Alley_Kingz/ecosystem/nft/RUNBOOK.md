# RUNBOOK -- Alley Kingz Metaplex Core mint (e5-mother)

**One line:** the phone generates metadata (pure Python, done), **e5-mother** installs tooling + uploads + creates the Core collection + deploys the Candy Machine + sets the Attribute Plugin, and **Rich signs every on-chain write with the Phantom wallet** (@bcardi, `2ef4VfuyRNYwu6WMW9TCz8cXpiqi23MSd8y8ZFyUmrBg`). Nothing on-chain happens on the phone. The AI never holds the key.

**Tooling confirmed live 2026-06-03:** `@metaplex-foundation/mpl-core` 1.10.0, `@metaplex-foundation/umi` 1.5.1, `@metaplex-foundation/mpl-core-candy-machine` (TokenPayment guard), Sugar CLI, `mplx` CLI. All open-source, free.

**Standard:** Metaplex Core (one on-chain account per asset, ~80% cheaper than Token Metadata) + the **Attribute Plugin** holding HP/damage/ability ON-CHAIN, mutable by the update authority only. Per `CHAIN_DECISION_MEMO.md`.

---

## GATES (do not start a gated step until its gate clears)

- **GATED ON ART:** the 48 `animation_url` Seedance clips + 48 images must exist and be pinned before upload/mint. Mythic batch lands first (`SEEDANCE_BATTLE_KIT.md`). Until then the metadata carries templated placeholder URIs (already generated).
- **GATED ON FUNDING:** the Phantom wallet must hold SOL for mint rent. Whole 48-card set rent ~= 0.0029-0.0037 SOL/card -> **~34 USD total**. Plus the $BCARDD mint price config (no cost to set). **LABELED SPEND:** ~$34 SOL rent for 48 cards; ~cents for optional Arweave permanence; $0 for all tooling + IPFS free tier.
- **GATED ON OPERATOR SIGNING:** every `create` / `deploy` / `mint` / `setPlugin` instruction is signed by Rich on e5-mother with the Phantom keypair. AI prebuilds the scripts; Rich runs + signs.

---

## STEP 0 -- Reach e5-mother  [RICH-on-e5-signs]
```bash
ssh e5-mother           # tailnet primary; or: ssh e5-mother-public (port 2222 break-glass)
```
The workspace mirrors to `/home/ubuntu/AA_MY_DRIVE` (symlinked), so all the paths below Just Work. `cd` into the nft dir:
```bash
cd /home/ubuntu/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/nft
```

## STEP 1 -- Install tooling ON e5-mother (never the phone)  [AI-prebuilt commands / RICH runs]
```bash
# node toolchain (e5-mother has working npm; the phone proot SIGSEGVs on npm install)
npm install -g @metaplex-foundation/cli            # the mplx CLI
npm install -g sugar                               # Sugar (or: bash <(curl -sSf https://sugar.metaplex.com/install.sh))
# project SDK (a local package.json mint script)
npm install @metaplex-foundation/umi-bundle-defaults \
            @metaplex-foundation/mpl-core \
            @metaplex-foundation/mpl-core-candy-machine
solana --version && node --version                 # receipts
```
Set the RPC (Helius/QuickNode free tier, DAS-enabled so we can read attributes back):
```bash
export RPC_URL="https://<HELIUS_FREE_TIER>.helius-rpc.com/?api-key=<KEY>"
```

## STEP 2 -- Upload assets, get CID bases  [RICH-on-e5-signs]   (GATED ON ART)
Follow `upload_assets.md`:
1. Pin `images/` -> IMAGE_CID_DIR. Pin `animations/` -> ANIMATION_CID_DIR (IPFS free tier).
2. Paste both into `asset_config.json`.
3. Re-run `python3 gen_metadata.py` (can run here or on the phone -- pure Python).
4. Pin `metadata/` -> METADATA_CID_DIR. Paste into `candy_machine_config.json` `prefixUri`.
5. Pin the collection image -> paste into `collection.json`.
   (Optional ~cents Arweave/Irys for the 5 hero videos -- LABELED SPEND.)

## STEP 3 -- Create the Core Collection  [RICH-on-e5-signs]
Reads `collection.json`. One collection holds the Core stat-cards (and later the Bubblegum dogs).
```bash
# umi + mpl-core createCollection, signed by the Phantom keypair
node mint/create_collection.mjs      # AI-prebuilt script (reads collection.json + asset_config.json)
# sets: name "Alley Kingz", symbol BCARDI, Royalties plugin (250 bps -> treasury), update authority = treasury multisig/PDA
# -> prints COLLECTION_ADDRESS  (paste into candy_machine_config.json collection.address)
```
**Operator decisions before this step** (CHAIN_DECISION_MEMO open items): who holds the **update authority** (recommend treasury multisig/PDA, not a single hot key); royalty bps (default 250).

## STEP 4 -- Deploy the Candy Machine  [RICH-on-e5-signs]   (GATED ON FUNDING)
Reads `candy_machine_config.json`. Fill every `<PLACEHOLDER>` first: `BCARDI_SPL_MINT_ADDRESS`, treasury ATA, prices, start date, allowlist merkle root.
```bash
sugar validate                       # checks config + metadata line up
sugar deploy                         # creates the Candy Machine + config lines (signed)
sugar guard add                      # applies the Candy Guard set (tokenPayment in $BCARDD, allowList, startDate, botTax, mintLimit)
sugar verify                         # confirms all 48 config lines uploaded
```
**$BCARDD is the mint currency** via the `tokenPayment` guard (mint = the $BCARDD SPL address, destination = treasury ATA). Coin-holder allowlist = the WL merkle root built on e5-mother.
**EDITIONS** (operator confirm, default = ECOSYSTEM_ARCHITECTURE Genesis ladder): Mythic cap 100 / Legendary 500 / Epic 2000 / Rare 10000 / Common uncapped via Bubblegum V2. Confirm whether $BCARDD #0001 is 1-of-1 before deploy.

## STEP 5 -- Set the Attribute Plugin (on-chain stats) per card  [RICH-on-e5-signs]
This is the "NFT IS the card" step. After a card asset exists (minted or pre-created), write its `onchain_attributes` block (from `metadata/<n>_<slug>.json`) into the Core Attribute Plugin.
```bash
node mint/set_attributes.mjs metadata/0001_bcardd.json    # AI-prebuilt
# writes the key/value string pairs: hp,damage,attack_speed,move_speed,range,cost,rarity,ability_id,queen_target
# authority = the collection update authority (treasury), so players cannot self-edit to cheat
```
Loop over all 48 metadata files. The Attribute Plugin can be attached at create time (preferred -- one tx per asset) or patched later by the update authority for balance changes.

## STEP 6 -- Mint / verify on Solscan + DAS  [RICH-on-e5-signs]
```bash
# Mythics first (matches Seedance phasing): mint $BCARDD #0001, confirm it lands in Phantom
sugar mint -n 1
```
Verify the stats are genuinely ON-CHAIN (receipt, not a claim) via the DAS API:
```bash
curl -s "$RPC_URL" -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"getAsset","params":{"id":"<ASSET_ADDRESS>"}}' | jq '.result.plugins'
# expect the Attribute Plugin with hp=2600, damage=160, ability_id=crownbreaker, queen_target=1
```
- Open the asset on **Solscan** -> confirm collection = Alley Kingz, attributes present, animation_url renders.
- Confirm it shows in the Phantom wallet next to $BCARDD (the one-wallet payoff).

## STEP 7 -- Log the decision + receipts  [AI-prebuilt]
Log the collection address, candy machine address, first-mint signature, and the DAS attribute read-back to Blinko so the mint is reproducible and proven.

---

## What the AI prebuilt vs what Rich does
| Item | Status |
|------|--------|
| `gen_metadata.py` + 48 metadata JSONs | [AI-prebuilt] DONE on the phone |
| `asset_config.json`, `collection.json`, `candy_machine_config.json` | [AI-prebuilt] skeletons with placeholders |
| `mint/create_collection.mjs`, `mint/set_attributes.mjs` | [AI-prebuilt on e5-mother] node scripts (built where npm works, not the phone) |
| Tooling install on e5-mother | [RICH-on-e5-signs] runs the npm/sugar installs |
| Seedance art + image production | [RICH] GATED ON ART (Seedance lane) |
| Fund the Phantom wallet with SOL rent (~$34) | [RICH] GATED ON FUNDING -- LABELED SPEND |
| Sign collection create / candy deploy / attribute set / mint | [RICH-on-e5-signs] every on-chain tx |
| Update-authority custody decision (treasury multisig/PDA) | [RICH] operator decision before STEP 3 |
| Editions ladder confirm (esp. $BCARDD #0001 1-of-1?) | [RICH] operator decision before STEP 4 |

## Cost summary (FREE-FIRST)
- Tooling (umi, mpl-core, candy machine, Sugar, mplx): **$0** (open-source).
- Storage: IPFS free tier **$0**; optional Arweave/Irys for 5 hero clips **~cents** (LABELED SPEND, SOL).
- RPC: Helius/QuickNode **free tier $0**.
- On-chain: mint rent **~$34 SOL for all 48 cards** (LABELED SPEND). Commons can route to Bubblegum V2 cNFTs (~$0.001 each) to push that lower.
- No audit bill (Metaplex programs are audited), no bridge, no SaaS.
