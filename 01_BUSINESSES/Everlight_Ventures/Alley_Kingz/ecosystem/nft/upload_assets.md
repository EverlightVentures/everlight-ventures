# UPLOAD ASSETS -- Alley Kingz NFT (FREE-FIRST storage plan)

**What gets uploaded:** 48 card images (PNG) + 48 Seedance battle clips (MP4) + 48 metadata JSONs + 1 collection image. All uploads run on **e5-mother** (the phone proot cannot npm/node install -- SIGSEGV -- and is not the storage host). The output is a CID base you paste into `asset_config.json`, then re-run `gen_metadata.py` so every metadata URI points at real, pinned media.

This is **GATED ON ART**: do not bulk-upload until the Seedance clips land (per `SEEDANCE_BATTLE_KIT.md`, Mythic batch first). You can upload placeholders to dry-run the pipeline, but the real CIDs only matter once art is final.

---

## 0. The order of operations

```
art lands (Seedance clips + images)
   -> upload IMAGES        -> get image CID dir
   -> upload ANIMATIONS    -> get animation CID dir
   -> swap both into asset_config.json
   -> re-run gen_metadata.py  (URIs now point at pinned media)
   -> upload the 48 metadata JSONs -> get metadata CID dir
   -> paste metadata CID dir into candy_machine_config.json prefixUri
   -> proceed to RUNBOOK.md mint steps
```

Three CID bases total: **images**, **animations**, **metadata**. Images + animations must be pinned BEFORE the metadata is generated (the JSON embeds those URIs). Metadata is pinned LAST.

---

## 1. Storage choice (FREE-FIRST, all paths costed)

| Option | Cost | Permanence | When to use | Verdict |
|--------|------|------------|-------------|---------|
| **IPFS free tier** (web3.storage / Filebase free / Pinata free) | $0 (free tier, no card on web3.storage) | Pinned while the service keeps it; re-pinnable | All 48 cards for launch; the default | **DEFAULT for the full set** |
| **Arweave via Irys** (formerly Bundlr) | pennies, pay in SOL (a few cents for the whole batch of MP4s) | PERMANENT (one-time pay, stored forever) | The 4 Mythic + 1 Legendary hero videos (the irreplaceable assets) | **LABEL SPEND: ~cents.** Upgrade hero assets only. |
| **NFT.Storage** | $0 free tier | Pinned | Fallback IPFS pinner | Backup option |

**Recommended split (free-first, then a labeled few cents):**
1. Pin all 48 images + 48 videos + 48 metadata to **IPFS free tier** -> $0.
2. OPTIONAL, operator spend call (CHAIN_DECISION_MEMO open item 4): re-upload the **5 hero videos** ($BCARDD, Jagged, Rosco, Crown Foxhound, Stonejaw) to **Arweave/Irys** for permanence. **LABELED SPEND: a few cents total, paid in SOL.** Everything else stays on free IPFS.

No paid SaaS. No pinning subscription required for launch volume.

---

## 2. IPFS free-tier upload (the default path, run on e5-mother)

Pick ONE pinner. web3.storage needs no credit card on the free tier.

### Option A -- web3.storage (w3 CLI)
```bash
# on e5-mother, NOT the phone
npm install -g @web3-storage/w3cli      # node lives on e5-mother
w3 login your-email@everlightventures.io   # email-link auth, free
w3 space create alley-kingz

# 1) images dir  -> note the returned CID
w3 up ./assets/images/        # contains 0001_bcardd.png ... 0048_*.png
# 2) animations dir -> note the returned CID
w3 up ./assets/animations/    # contains the Seedance MP4s (exact filenames from SEEDANCE_BATTLE_KIT)
```

### Option B -- Filebase / Pinata (S3-style or pinning API, free tier)
Equivalent: upload the `images/` and `animations/` directories, record each directory CID.

After both uploads you have:
- `IMAGE_CID_DIR`     e.g. `bafybe<...images...>`
- `ANIMATION_CID_DIR` e.g. `bafybe<...animations...>`

---

## 3. Swap CIDs into asset_config.json + regenerate

Edit `asset_config.json`:
```json
"storage_provider": "ipfs",
"image_cid_base":     "ipfs://bafybe<...images...>",
"animation_cid_base": "ipfs://bafybe<...animations...>",
"gateway_https":      "https://w3s.link/ipfs/<CID>"
```
Confirm the filename patterns still match what you uploaded:
- images: `{cardNumber}_{slug}.png`  (e.g. `0001_bcardd.png`)
- animations: `{animation_date_prefix}_AKBattle_{anim_token}_Seedance_V1.mp4`
  (e.g. `2026-06-02_AKBattle_$BCARDD_Crownbreaker_Seedance_V1.mp4`)

If the real Seedance clips use a different date or version suffix, update `animation_date_prefix` (and the pattern) so the URIs match the actual files. Then on the phone (pure Python, no install):
```bash
python3 gen_metadata.py     # re-emits all 48 metadata/*.json with the real media URIs
```

## 4. Upload the metadata (LAST), get the metadata CID

```bash
# on e5-mother, after gen_metadata.py has the real media URIs baked in
w3 up ./metadata/           # the 48 JSON files
# -> METADATA_CID_DIR
```
Paste it into `candy_machine_config.json`:
```json
"configLineSettings": { "prefixUri": "ipfs://<METADATA_CID_DIR>/" }
```
And the collection image CID into `collection.json` (`image` + `properties.files[0].uri`).

## 5. OPTIONAL permanence upgrade for hero videos (LABELED SPEND ~cents)

```bash
# e5-mother, Irys CLI -- pays in SOL, a few cents for the 5 hero MP4s
npm install -g @irys/cli
irys upload ./assets/animations/2026-06-02_AKBattle_$BCARDD_Crownbreaker_Seedance_V1.mp4 \
  -n mainnet -t solana -w <KEYPAIR>     # operator-signed, returns a permanent ar:// URI
```
Swap those 5 `animation_url` values to the returned `https://arweave.net/<txid>` (or `ar://`) URIs in the Mythic/Legendary metadata, then re-pin those JSONs. Everything else stays free IPFS.

---

## Verification receipts (prove, do not claim)
- After each `w3 up`, record the CID + a working gateway URL that returns the asset (HTTP 200).
- After re-running gen_metadata.py, open `metadata/0001_bcardd.json` and confirm `image` + `animation_url` resolve in a browser.
- Log the CID bases to Blinko so the mint step is reproducible.

**Cost line:** IPFS free tier = $0. Optional Arweave/Irys for the 5 hero clips = a few cents, paid in SOL, operator-signed. No other spend.
