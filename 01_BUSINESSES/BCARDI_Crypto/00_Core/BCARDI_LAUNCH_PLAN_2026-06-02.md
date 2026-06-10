# $BCARDD Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Get $BCARDD founded and live on Solana via pump.fun, with a face, a home, socials, and a locked 9% founder bag -- for ~3 SOL (~$250).

**Architecture:** AI builds 100% of the off-chain launchpad (assets, copy, site, socials structure, runbook). Rich executes the ~5-minute on-chain launch (wallet, fund, create, dev-buy, lock) -- AI never touches keys or signs transactions.

**Tech Stack:** pump.fun (Solana), Phantom wallet, Proton Pass (secrets), Cloudflare Pages (static site, no npm needed -- respects phone-proot limits), X / Telegram / Discord.

**Live numbers (verified 2026-06-02, SOL ~$79):** creation FREE · 9% dev buy ~2.75 SOL (~$217) · graduation at ~85 SOL raised · creator gets 0.5 SOL on graduation + ongoing fees. Re-verify at launch (Phase 0).

---

## Division of labor
- **[AI]** = Claude builds it, no keys involved.
- **[RICH]** = on-chain / account-owning action only Rich can do (his money, his keys). AI provides the exact content + click-by-click.

---

## Phase 0: Pre-flight verification  [AI]

### Task 0: Confirm live pump.fun params before spending
**Files:** none (research, logged to plan)

- [ ] **Step 1:** WebSearch current pump.fun fee model + creator-fee rate + graduation threshold (params change).
- [ ] **Step 2:** Recompute exact SOL for a 9% dev buy against the live bonding curve; decide single-buy vs laddered (a one-tx 9% buy pushes entry price up ~19%).
- [ ] **Step 3:** Confirm lock tool that supports pump.fun/PumpSwap SPL holdings (Streamflow or Jupiter Lock).
- [ ] **Step 4 (verify):** Record final numbers in this file under "Live numbers." Expected: dev-buy SOL figure within ~2-4 SOL.

---

## Phase 1: Brand assets  [AI]

### Task 1: Produce the coin logo (face = Official_BCARDI.png)
**Files:**
- Source: `01_BUSINESSES/BCARDI_Crypto/01_Media/BCARDI_OFFICIAL_COIN.png` and `Everlight_Crypto/Official_BCARDI.png`
- Create: `01_BUSINESSES/BCARDI_Crypto/01_Media/launch/bcardi_logo_512.png`

- [ ] **Step 1:** Pick the cleanest source PNG; crop/pad to exactly 512x512 (pump.fun + DEX standard) via Pillow.
- [ ] **Step 2 (verify):** `python3 -c "from PIL import Image;i=Image.open('.../bcardi_logo_512.png');print(i.size, i.format)"` -> Expected: `(512, 512) PNG`, file < 200 KB.

### Task 2: Stage the NFT video (the live dealer MP4)
**Files:**
- Source: `01_BUSINESSES/Everlight_Ventures/Everlight_Gaming/Blackjack/Official_BCARDI_LIVE_DEALER.mp4`
- Create: `01_BUSINESSES/BCARDI_Crypto/01_Media/launch/bcardi_nft_dealer.mp4` (copy) + `bcardi_nft_thumb_512.png`

- [ ] **Step 1:** Copy the MP4 into `launch/`; generate a 512x512 thumbnail (ffmpeg first frame on e5-mother if phone can't).
- [ ] **Step 2 (verify):** Both files exist and play; thumbnail is 512x512. (NFT mint itself is a later/optional plan -- this just stages assets.)

---

## Phase 2: Copy pack  [AI]  (real copy, no placeholders)

### Task 3: Write the canonical copy file
**Files:** Create `01_BUSINESSES/BCARDI_Crypto/02_Community/COPY_PACK.md`

- [ ] **Step 1:** Write these exact assets into the file:
  - **Disclaimer (every surface):** "$BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited. Not financial advice."
  - **One-liner:** "The dog with his own dealer. $BCARDD -- a meme coin on Solana with a blackjack table behind it."
  - **X bio (160 char):** "The realest dog in crypto. $BCARDD on Solana. He deals blackjack. Not affiliated w/ Bacardi Ltd. Not financial advice. 🐶🃏"
  - **Pinned launch tweet:** [3-line hook + contract address placeholder token `<CA>` to fill at launch + pump.fun link + "LP auto + dev bag locked"].
  - **Telegram welcome + pinned rules.**
  - **Discord welcome + channel charter.**
- [ ] **Step 2 (verify):** File contains all 6 blocks, disclaimer present in each public-facing one, every block under its platform char limit.

### Task 4: Brand-voice + compliance pass
- [ ] **Step 1:** Run the copy through the everlight_humanizer + everlight_copy_guard skills (strip AI tells, match Rich's voice).
- [ ] **Step 2 (verify):** No "investment/returns/guaranteed/profit" promises anywhere (legal guardrail). Grep the copy file for those words -> Expected: only inside the "NEVER say" note.

---

## Phase 3: Socials skeleton  [RICH creates accounts, AI supplies everything]

### Task 5: Stand up X + Telegram + Discord
- [ ] **Step 1 [RICH]:** Create the X account, Telegram group, Discord server (or buddy does Discord). Set handles.
- [ ] **Step 2 [AI]:** Drop in bios/avatars (logo_512), pinned posts, Telegram rules, Discord channels (#announcements #general #how-to-buy #memes #raids) + welcome bot text from COPY_PACK.
- [ ] **Step 3 (verify):** Each link resolves (HTTP 200 / valid invite), disclaimer in each bio, logo set.

---

## Phase 4: Landing page  [AI build, RICH owns domain]

### Task 6: Build the one-page static site
**Files:** Create `01_BUSINESSES/BCARDI_Crypto/site/index.html` (+ `/assets/`)

- [ ] **Step 1:** Single self-contained static page (no npm -- phone-proot safe): hero (logo + dealer MP4 loop), the dog's story, "How to buy" (Phantom -> pump.fun, 4 steps), live links (X/TG/Discord), contract address slot, disclaimer footer. Everlight gold theme reused.
- [ ] **Step 2 (verify local):** `python3 -m http.server` in `site/`, curl localhost -> HTTP 200, grep page for disclaimer + all 3 social links present.
- [ ] **Step 3 [RICH/AI]:** Deploy to Cloudflare Pages (free) on a `bcardi.everlightventures.io` subdomain (or `/bcardi` route). Per network-binding doctrine: public-by-design via ev domain = allowed.
- [ ] **Step 4 (verify live):** `curl -sI https://bcardi.everlightventures.io` -> HTTP 200, Cloudflare header, title contains "BCARDI".

---

## Phase 5: Secure the launch wallet  [RICH]

### Task 7: Fresh Phantom wallet (never-exposed)
- [x] **Step 1 [RICH]:** DONE -- fresh Phantom Google-login wallet @bcardi, address `2ef4VfuyRNYwu6WMW9TCz8cXpiqi23MSd8y8ZFyUmrBg`. No seed-in-file (good). Validated on-chain 2026-06-02.
- [ ] **Step 1b [RICH]:** Harden it: Gmail authenticator/passkey 2FA (NOT SMS) + export private key to Proton Pass (lockout backup).
- [ ] **Step 2 [RICH]:** Fund it with ~3 SOL (~$250) + a small buffer. (Currently 0 SOL.)
- [ ] **Step 3 (verify):** Phantom + Solscan show >= 3 SOL at `2ef4...UmrBg`. (Prereq: finish the Proton import + run `setup/shred_plaintext_secrets.sh`.)

---

## Phase 6: LAUNCH DAY  [RICH executes, AI on standby live]

### Task 8: Create + dev-buy + lock
- [ ] **Step 1 [RICH]:** On pump.fun: Create coin -> name "Bacardi", ticker `BCARDI`, upload `bcardi_logo_512.png`, paste description + disclaimer + social links from COPY_PACK.
- [ ] **Step 2 [RICH]:** In the SAME flow, set the **initial dev buy to the Phase-0 SOL figure (~2.75 SOL) targeting ~9%**. Confirm.
- [ ] **Step 3 [RICH]:** Immediately move 3% (30M) to the labeled treasury wallet.
- [ ] **Step 4 [RICH]:** Lock/vest the 9% founder bag (Streamflow/Jupiter Lock, 3-6mo). Copy the public lock URL.
- [ ] **Step 5 (verify):** Solscan shows: coin live, founder wallet holdings locked (lock URL resolves), treasury wallet funded. Screenshot for records.

### Task 9: Go-live broadcast
- [ ] **Step 1 [AI]:** Fill `<CA>` (contract address) into the pinned tweet, Telegram pin, Discord #announcements, and the site contract slot.
- [ ] **Step 2 [RICH/buddy]:** Post pinned tweet, pin TG/Discord messages, post first airdrop teaser.
- [ ] **Step 3 (verify):** CA matches everywhere (grep/compare), lock link public, "dev bag locked" stated in the pin. Trust signals live.

---

## Deferred to a SEPARATE plan (post-traction, not needed to launch)
- Creator-fee -> buyback-and-burn automation.
- Full airdrop distribution tooling (snapshot + send).
- In-game integration: $BCARDD as blackjack chips, holder-only tables, dealer skins, NFT-as-OG-badge.
- NFT mint of the dealer video.

---

## Self-review notes
- Spec coverage: positioning (T3), assets (T1-2), economics/dev-buy (T0,T8), lock (T8), treasury (T8), socials/site/disclaimer (T3-6), guardrails (T4), fresh wallet (T7), build-time verifications (T0). All mapped.
- Legal guardrail enforced in T4 (no returns promises).
- Phone-proot constraint respected: static HTML site (no npm); heavy media ops routed to e5-mother.
- Cost honesty: ~3 SOL total, build is $0.

*Plan written 2026-06-02. Spec: `BCARDI_SOLANA_RELAUNCH_SPEC_2026-06-02.md`. Memory: [[project_bcardi_meme_coin]].*
