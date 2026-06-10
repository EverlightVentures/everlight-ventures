# $BCARDD -- X (Twitter) Launch Kit
**The opening + advertising channel. Built to run hands-off.**
Updated 2026-06-02.

## 1. Profile setup (one-time, Rich/buddy does the account creation)
- **Handle:** @bcardicoin (first choice) -> @bcardidog -> @bcardisol if taken. Avoid plain @bcardi (rum brand, likely taken, and we stay clearly the DOG, not the liquor).
- **Display name:** Bacardi 🐶🃏 ($BCARDD)
- **Profile pic:** `01_Media/launch/bcardi_logo_512.png`
- **Banner:** 1500x500. Use a wide crop of the dealer scene + the line "The dog with his own table. Solana." (generate on e5/PC; phone proot cannot do heavy media).
- **Bio (118 chars, from COPY_PACK):** "The realest dog in crypto. $BCARDD on Solana. He deals blackjack. Not affiliated w/ Bacardi Ltd. Not financial advice. 🐶🃏"
- **Pinned:** the launch tweet (`launch-01` in the queue) once the coin is live.
- **Link:** everlightventures.io/bcardi once deployed.

## 2. How the content runs itself
- Engine: `automation/x_autopilot.py` + `automation/x_content_queue.json`.
- It drips the next queued tweet each scheduled run, runs a **compliance gate** (blocks any profit/returns/moon-promise -- legal guardrail) before anything posts, and logs every post.
- `--refill N` auto-generates fresh on-brand sustain tweets (Anthropic) so the queue never runs dry.
- Runs on **e5-mother via cron** (the phone cannot host it -- PRoot kill-on-exit). Cron line is in the script header.
- Secrets (X API keys) live in env / Proton Pass, never in the repo.

## 3. Content phases (already loaded in the queue)
- **tease (6 posts):** curiosity, no contract address. Drip these starting now to warm up the page before the coin exists.
- **launch (1 post):** auto-held until `BCARDI_CA` + `BCARDI_PUMP_URL` env are set on launch day, then it fires.
- **sustain (8+ posts):** memes, community prompts, trust receipts. Refill on a schedule.

## 4. Go-live steps for the operator (X side)
1. Create the @bcardicoin account; set pic/banner/bio/link above.
2. On e5: `pip install tweepy`; put X API keys (OAuth 1.0a) in env; add the cron line.
3. `python3 x_autopilot.py --status` then `--dry-run` to confirm, then let cron drive.
4. Launch day: set `BCARDI_CA` and `BCARDI_PUMP_URL` env -> the launch tweet fires automatically and gets pinned.

## 5. Getting the X API keys (free tier is enough to start)
- developer.x.com -> create a Project + App -> generate API Key/Secret + Access Token/Secret (with Read+Write).
- Free tier allows limited posts/month -- fine for a tease + daily drip. Upgrade only if volume demands it (free-first).

*See `AUTOMATION_GAMEPLAN.md` for the full hands-off operating model and the Discord/Telegram phase.*
