# Everlight x $BCARDD x Alley Kingz -- MASTER EXECUTION CHECKLIST
**Date:** 2026-06-03 | **For:** Rich (or a delegate / buddy) | **Rule:** the AI built everything off-chain; every box below needs your art, money, or signature.

Tags: **[DONE]** built + verified · **[RICH]** only you can do (keys/money) · **[e5]** runs on e5-mother, not the phone (proot cannot npm/Unity/render) · **[AI]** I do it on your go.

> **THE SEQUENCE (do not skip):** Coin ships FIRST (it is closest + funds + audiences everything), then art, then NFT, then game/arcade. Do not let the big game build delay the coin.

---

## PHASE 0 -- SECURITY (do this first, it protects every wallet)
- [ ] **[RICH]** Import `03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json` at pass.proton.me (Settings -> Import -> Bitwarden). 43 secrets, 11 folders.
- [ ] **[RICH]** Run `bash 03_AUTOMATION_CORE/01_Scripts/setup/shred_plaintext_secrets.sh` (type YES) to wipe the plaintext copies.
- [ ] **[RICH]** Harden the @bcardi wallet Gmail: authenticator/passkey 2FA (NOT SMS) + export the wallet private key into Proton Pass (lockout backup).
- [ ] **[RICH]** Rotate the other exposed live keys flagged in `reference_crypto_seed_vault` (Stripe live, Supabase service-role, Cloudflare, Twilio) when you get a window.

## PHASE 1 -- $BCARDD COIN (ships first)
- [x] **[DONE]** Coin logo (512), copy pack, X autopilot + queue, premium landing site (preview `localhost:8513`), launch spec + plan.
- [ ] **[RICH]** Fund wallet `2ef4VfuyRNYwu6WMW9TCz8cXpiqi23MSd8y8ZFyUmrBg` with ~3 SOL (~$250). Currently 0.
- [ ] **[RICH]** Create the **@bcardicoin** X account + grab free X API keys (handles in COPY_PACK.md).
- [ ] **[AI/e5]** Deploy the site to `everlightventures.io/bcardi` (static page; git push or e5 build).
- [ ] **[RICH + AI]** Create the coin on pump.fun: name $BCARDD, ticker BCARDI, logo, description + links. **Dev-buy ~2.75 SOL for 9%.** I narrate every click; you sign.
- [ ] **[RICH]** Immediately: move 3% to treasury, **lock the 9% founder bag** (Streamflow/Jupiter Lock), copy the lock URL.
- [ ] **[AI]** Fill the live contract address `<CA>` into the site, X pin, copy pack.
- [ ] **[e5]** Arm `x_autopilot.py` on an e5-mother cron (2-3 posts/day, compliance-gated).

## PHASE 2 -- SEEDANCE ART (the hype set)
- [ ] **[RICH]** Confirm the live Seedance credit balance (free-first: do not bulk-buy).
- [ ] **[RICH/e5]** Generate Batch 1 from `ecosystem/SEEDANCE_BATTLE_KIT.md`: 4 Mythic hero clips + 5-shot war trailer (~3,000 credits). Paste prompts are ready.
- [ ] **[AI]** Run each clip through the Art Review Gate (`VISUAL_AI_PIPELINE_SOP.md` Stage 4). No slop.
- [ ] **[AI]** Wire the clips: coin teaser (X/site), arcade hero loop, and the NFT `animation_url` slots.

## PHASE 3 -- SOLANA NFT MINT (Metaplex Core)
- [ ] **[RICH]** Decide: update-authority custody (recommend a treasury wallet/multisig) + is **$BCARDD #0001 a true 1-of-1**?
- [x] **[DONE]** Pipeline built: `ecosystem/nft/` (gen_metadata.py, 48 metadata JSONs, collection.json, candy_machine_config.json, RUNBOOK.md).
- [ ] **[e5 + RICH signs]** Follow `ecosystem/nft/RUNBOOK.md`: install Sugar/umi on e5, upload assets to IPFS (free), plug CIDs into gen_metadata, create the Core collection, deploy the candy machine ($BCARDD-priced), set the Attribute Plugin, mint. ~$34 SOL total. You sign every tx with @bcardi.
- [ ] **[AI/RICH]** Verify the collection + a sample card on Solscan.

## PHASE 4 -- GAME / EVERLIGHT ARCADE
- [x] **[DONE]** Playable prototype with the real 48-card canon (preview `localhost:8531`): canon.js + engine.js + index.html, Everlight-themed.
- [ ] **[RICH]** Playtest it; tell me what to tune (balance, feel, art).
- [ ] **[e5]** Mount in the website arcade per `ecosystem/game/ARCADE_MOUNT.md` (iframe or copy into vantaris/public; Next build runs on e5).
- [ ] **[e5]** Bind NFT ownership -> playable card unlock; $BCARDD as the in-game currency + chip.

## PHASE 5 -- METAVERSE (later, optional, not a dependency)
- [ ] Dog crews + rigs become 3D avatars/vehicles (Unity ArenaAdvance is the seed). Build the startup first.

---

## OPERATOR DECISIONS STILL OPEN
1. $BCARDD #0001 = 1-of-1, or capped edition? (Phase 3)
2. NFT update-authority custody (recommend treasury multisig). (Phase 3)
3. Legal posture sign-off: utility/cosmetic, never promised returns. Loop the legal team before the marketplace + any pack/loot-box mechanic. (gates Phase 3/4 marketplace)
4. Web-first Arcade build vs Unity mobile (recommend web-first). (Phase 4)
5. Marketplace venue: Tensor / Magic Eden first. (Phase 4)

## LIVE PREVIEWS (right now, on the phone)
- Coin site: `http://localhost:8513`
- Alley Kingz playable: `http://localhost:8531`

## CANONICAL DOCS
- Coin: `BCARDI_Crypto/00_Core/BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md` + `BCARDI_LAUNCH_PLAN_2026-06-02.md`
- Ecosystem: `Alley_Kingz/ecosystem/MASTER_BUILD_PLAN.md` (+ chain/roster/seedance/economy/reuse docs)
- Canon data: `Alley_Kingz/ecosystem/data/` | NFT: `ecosystem/nft/` | Game: `ecosystem/game/`

*Built across the 2026-06-02/03 sessions. Memory: [[project_bcardi_meme_coin]], [[project_alley_kingz_ecosystem]], [[reference_crypto_seed_vault]].*
