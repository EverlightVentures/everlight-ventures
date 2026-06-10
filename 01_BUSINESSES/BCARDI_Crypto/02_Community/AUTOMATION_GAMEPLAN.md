# $BCARDD -- Hands-Off Automation Game Plan
**Rich's directive: "I don't want anything to do with it. Create the coin, use X to tease, grow, then add Telegram or Discord, automate the content of it all, reach its potential, I cash out and leave."**
Updated 2026-06-02. This is the operating model that makes that real.

## The phased rollout (deliberately simple first)
1. **Phase A -- X only (now).** X is the single opening + advertising channel. Tease drip runs on autopilot (`x_autopilot.py`). No community to moderate yet, so nothing for Rich to do. This is live-ready today minus the X account + API keys.
2. **Phase B -- launch the coin.** Set the contract env vars; the launch tweet auto-fires and pins. X keeps dripping sustain content + refills itself.
3. **Phase C -- add ONE community channel once there is traction.** Recommendation: **Telegram first**, not Discord. Why: crypto traders live on Telegram, it is lower-overhead, and a single auto-posting bot can run it. Discord is richer but needs real moderation/roles -- add it later only if the community gets big. (Full Discord kit already built in `DISCORD_SETUP.md` for when that day comes; hand it to the buddy.)
4. **Phase D -- full content automation across channels.** One content engine feeds X + Telegram (+ Discord) from the same queue + compliance gate.

## The automation architecture (one brain, many mouths)
- **Content queue** (`x_content_queue.json`): the source of posts. Editable by hand or refilled by AI.
- **AI refill** (`--refill N`): generates fresh on-brand posts (dog + casino voice) using Anthropic, so it never runs dry. Tune cadence on cron.
- **Compliance gate** (built in): every post is screened for banned promise-of-profit language BEFORE it sends. This is the legal seatbelt for unattended posting. Hype the dog, not the money.
- **Scheduler:** cron on **e5-mother** (always-on; the phone cannot host it). 2-3 drips/day for X, similar for Telegram later.
- **Cross-post adapter (Phase D):** add `telegram_autopilot.py` that reads the SAME queue and posts via a Telegram bot token (free). Discord via webhook the same way. One queue, one gate, three outputs.
- **Secrets:** all API tokens in env / Proton Pass. Never in the repo.

## Hype tactics (automatable)
- Daily GM + nightly "table's open" posts (drip).
- Meme posts + "tag a degen" engagement prompts (refill keeps these fresh).
- Trust-receipt posts ("dev bag locked, verify on-chain") -- trust is the conversion lever for a fair-launch coin.
- Reply automation can come later, but START with scheduled posting only -- unattended auto-replies are a compliance/impersonation risk until the gate is proven.

## "I cash out and leave" -- the exit + succession note
- The bag is **illiquid**: cashing out means selling **gradually into real liquidity**, not one dump (a dump is a self-rug and tanks the very community that gave it value). Telegraph it.
- The automation does NOT need Rich day-to-day once cron is set -- that is the whole point. It self-runs and self-refills.
- **Succession:** if someone else takes the project, the handoff is: the @bcardicoin login + the e5 cron + the X/Telegram API keys (in Proton Pass) + these docs. Anyone can run it from the queue + gate. A `HANDOFF.md` should be written before any exit so the project can outlive the founder's attention -- which is also what keeps the token alive after Rich steps back.
- Reality check (Operator Truth): most meme coins fade. "Reach its potential and cash out" is the goal; the honest plan maximizes the odds and the dignity of the exit, it does not promise the moon.

## What is needed from Rich (the only manual bits)
1. Create the **@bcardicoin** X account (Phase A).
2. Get **X API keys** (free tier) -> put in e5 env.
3. **Fund the wallet** + the 5-minute pump.fun launch (Phase B).
Everything else runs on autopilot.
