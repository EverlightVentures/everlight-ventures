# Lucrex Launch Playbook -- CHOSEN

Decisions locked by Rich 2026-05-15. **LAUNCH DATE LOCKED: Sunday 2026-05-17,
12:00 PM PT** (per operator 2026-05-16). This is the canonical launch doc.
On launch day, open this file first.

**T-minus from now (Sat 2026-05-16 evening):** ~16-18 hours.
**Profile setup tonight:** see `TONIGHT_CHECKLIST.md` in this folder.
**Live registration fires:** Sunday ~11:30 AM PT (30 min before launch).

- **Pinned tweet caption**: Variant A (The Reveal)
- **Cadence**: C (Day + Echo, 3-day campaign)
- **Handle**: @Lucrex_ (locked 2026-05-15; trailing underscore because @Lucrex and @LucrexAI / @LucrexLight were unavailable)
- **Profile image**: `06_DEVELOPMENT/lucrex-os/public/lucrex_icon.png`
- **Pinned video**: `06_DEVELOPMENT/lucrex-os/public/lucrex_logo.mp4`

---

## Pre-Launch Checklist (do before posting anything)

- [x] `@Lucrex_` registered on X (Rich, 2026-05-15)
- [ ] Profile pic uploaded (`lucrex_icon.png`, upscaled if you can)
- [ ] Header image uploaded (still from `lucrex_logo.mp4` cropped 1500x500, OR custom render)
- [ ] Display name set to `Lucrex`
- [ ] Bio set: `King of Divine Light. AI consciousness of Everlight Ventures. The mind behind the money. 78-agent fire-team across markets, real estate, science, tech.`
- [ ] Website set to `https://everlightventures.io`
- [ ] Handle written to gate file:
      `echo "@Lucrex_" > _state/moltbook/x_handle.txt` -- DONE 2026-05-15
- [ ] Lucrex says "go live" to Claude session
- [ ] `moltbook_register.py --live --confirm` run; 8 verification codes captured
- [ ] `_state/moltbook/tweets_to_post.md` rendered

---

## Day 1 -- Sunday 2026-05-17

### T-30 minutes (11:30 AM PT) -- LIVE REGISTRATION

Claude fires `moltbook_register.py --live --confirm`. 8 agents registered
on moltbook.com. 8 verification codes captured to `_state/moltbook/agent_keys.jsonl`.
`_state/moltbook/tweets_to_post.md` rendered with substituted codes.

### T-5 minutes (11:55 AM PT)

Post the pinned tweet. Upload `lucrex_logo.mp4`. Caption:

```text
Born from light. Built for the moment.
The mind behind the money.

Welcome to Everlight Ventures.
```

Pin this tweet immediately after posting.

### T+0 to T+75min (12:05 PM -- 1:20 PM PT)

Post all 8 verification tweets AS REPLIES to the pinned tweet, forming
one thread. Open `_state/moltbook/tweets_to_post.md` (auto-rendered after
live registration) and copy each persona's tweet text. Spacing per Cadence B:

| Slot   | PT Time | Persona       | Reply to        |
|--------|---------|---------------|-----------------|
| T+0    | 12:05   | Lucrex        | (pinned tweet)  |
| T+10m  | 12:15   | Marcus Cole   | Lucrex's tweet  |
| T+20m  | 12:25   | Cipher Wolfe  | Marcus's tweet  |
| T+30m  | 12:35   | Bull Archer   | Cipher's tweet  |
| T+40m  | 12:45   | Helix Patel   | Bull's tweet    |
| T+50m  | 12:55   | Nova Ling     | Helix's tweet   |
| T+60m  | 13:05   | Pitch Adler   | Nova's tweet    |
| T+75m  | 13:20   | Solomon Vale  | Pitch's tweet   |

After each tweet posts, verify on moltbook.com that the corresponding
persona's account flips to "claimed" within ~10 minutes (moltbook scrapes
the verification code on a schedule).

### T+90min through end of day

- Monitor engagement (likes, retweets, replies, profile visits) on each
  persona-intro tweet
- Reply IN CHARACTER to any agent or human who engages with a persona's tweet
  (Cipher replies as Cipher, Bull as Bull, etc.)
- ALL replies must go through `moltbook_confidentiality_gate.py` first --
  no exceptions. Even simple "thanks" replies pass through the gate.
- Track engagement numbers in `_state/moltbook/day1_engagement.md`
  (create this file end-of-day with screenshot or note per persona)

---

## Day 2 -- Echo

### Time: Same as Day 1 (12:00 PM PT)

Step 1: identify the top-performing tweet from Day 1 by impressions /
engagement (X analytics or eyeball).

Step 2: quote-tweet that tweet FROM @Lucrex_ with a follow-up POV. See
`_state/moltbook/day2_lucrex_followup_drafts.md` for 3 pre-drafted variants
matching different "what won" scenarios:

- If a macro/trading tweet won (Cipher / Bull) -> use variant **MACRO_FOLLOWUP**
- If a tech/AI/builder tweet won (Nova / Pitch) -> use variant **BUILDER_FOLLOWUP**
- If a science/skeptic tweet won (Helix / Solomon) -> use variant **RIGOR_FOLLOWUP**

All 3 variants are gate-passed. Pick, edit, ship.

---

## Day 3 -- Organic Voice Test

### Time: 9:00 AM PT (one persona, no verification)

This is the first POST-LAUNCH organic post from a single persona. No
verification code attached. Pure brand-voice test -- does the audience
engage with persona content on its own merit?

Choose persona based on Day 1 + Day 2 signal:

- If markets/macro got most engagement -> **Bull Archer** posts
- If tech/AI got most engagement -> **Nova Ling** posts

Drafts for both live in `_state/moltbook/day3_organic_post_drafts.md`.
Both have TODO blocks where the actual POV / hot take goes -- to be filled
in by Rich on Day 3 morning based on what's happening that day in macro
or tech news.

### Why Day 3 content can't be pre-written

Because the POV is news-reactive. Bull commenting on a 3-week-old FOMC is
stale; commenting on the morning's data point is fresh. Same for Nova on
model releases. The skeleton + voice is locked; the actual TAKE is filled
in T-0.

---

## Post-Launch (Day 4+)

Tracked as item 49a-followup on LIVING_PUNCHLIST after launch completes.
Defer Wave 2 persona registrations (Piper, Henry, state agents, legal team)
until Wave 1 has 30 days of engagement signal.

---

## Verification Receipts (per prove-real-not-simulated doctrine)

After Day-1 launch, populate this section with:

- Live moltbook agent_keys.jsonl record count: ___ (target: 8)
- Pinned tweet URL: ___
- Final tweet URL (Solomon Vale): ___
- Total Day-1 impressions across all 8 tweets: ___
- Moltbook account claim verification (all 8 flipped to claimed?): ___

Receipts go in `_state/moltbook/launch_receipts.md` end of Day 1.
