# ALLEY KINGZ -- PHASE-2 SOCIAL FEATURE + MODERATION SPEC (deep-dive 2026-06-19)
The Clan Yard: best-of-IG + best-of-X + best-of-game-lobbies, built ON the already-staged social layer.
Anchored: supabase/migrations/20260614000000_social_layer.sql + 20260614010000_grants_donations.sql, game/social.js, SOCIAL_LAYER_ARCHITECTURE.md

## 0. GROUND TRUTH -- already exists (do NOT rebuild); this spec is the engagement SKIN on top
- `ak_chat_messages` (world/crew scope, 1-200, faction tag, Realtime, last-50) -> channels + live chat
- Presence via channel.track on ak:world + ak:crew:<id> -> online roster + green dots (social.js paints `_on`)
- `ak_crew_members` (role, last_seen, donated_week, received_week, fame_week) -> social graph + weekly leaderboard
- `ak_donation_requests` + `ak_donations` + don-fill/don-request -> carry-your-weight loop (wired)
- `ak_grants` (server->client economy rail, claimed-on-load, Realtime) -> the reward pipe for EVERY new hook
- `ak_chat_bans` + `ak_chat_reports` -> moderation backbone
- Edge fns ak-crew + ak-chat (rate-limit + profanity + ban-check) = the ONLY writers; RLS forced, anon read-only
- pg_cron weekly reset (Mon 08:00 UTC) + nightly chat prune -> scheduler pattern for streaks/flex
**Design law:** every new mechanic = (a) a column on an existing table, (b) a thin ak_-prefixed table written ONLY by an edge fn, or (c) a payout via ak_grants. No new always-on infra in Phase 2 (realtime 2v2 = Phase 3).

## 1. FEATURE SET -- ranked by retention-ROI / build-cost
### TIER 1 (Phase 2 MVP, all reuse staged tables)
1. **One-tap reactions** on chat/feed items -- fixed set 🔥/👑/GG/🐶 (no free emoji = no mod surface). [IG likes] [M]. New `ak_reactions(target_type,target_id,user_id,emoji)` unique per user/item; written by ak-chat {react}; threshold (5 🔥) -> ak_grants gold ("your clutch got 5 🔥 +20g").
2. **Crew Activity Feed** ("what'd I miss?") -- bounded feed: "Rex hit Arena 9", "Maya donated 6x Jolt", "new card pulled". [IG/X feed] [M]. New `ak_crew_feed(crew_id,kind,actor,payload,created_at,expires_at?)`; events already fire in ak-crew + battle-end -> just insert a feed row; crew-scoped RLS (reuse ak_is_crew_member); renders above the donation board.
3. **@-mentions** (`@Rex` highlights + pings) -- strongest re-engagement after DMs. [X mentions] [M]. ak-chat parses @name vs roster, stores mentions[] on the msg, writes ak_notifications rows.
4. **Crew streak with freezes** ("12 of 15 played today") -- social streaks run 34% longer. POSITIVE proof only (never "3 of 15"), freezes so life doesn't nuke it. [streaks] [M]. Add streak_days/last_streak_date/freeze_tokens to ak_crews; daily pg_cron rolls it (>=60% played -> ++, else freeze, else reset); milestone days (7/30/100) pay the crew via ak_grants.
5. **Social notifications** (in-app badge MVP, web-push fast-follow) -- fire ONLY on: @-mentioned, your donation request filled, crew needs you for war, your clip crossed a reaction threshold. [notifications, disciplined] [M]. `ak_notifications(user_id,kind,body,link,read)`, owner-scoped RLS (copy ak_grants policy), Realtime bell.

### TIER 2 (Phase 2 if time, else fast-follow)
6. **Weekly crew donation leaderboard** (friend/peer-banded beats global) [S] -- donated_week already exists+zeroed weekly; sorted roster view + 👑 top donor; weekend "double donation" = an edge-fn flag.
7. **24h "Crew Flex"** ephemeral highlight (auto-gen highlight card, not video -- AK is 2D) [M] -- reuse ak_crew_feed kind='flex' + expires_at; nightly prune already deletes; reactable.
8. **Quote/share-to-crew** a clutch moment [S] -- a button that re-posts a feed/flex item to crew chat; just ak-chat {send} with a structured payload.

### TIER 3 (defer to Phase 3+)
9. 1:1 DMs / private group chat -- deepest bonds but a new private scope + much bigger moderation surface. Defer.

## 2. LOBBY HANDLING
Two scopes: WORLD chat (everyone, the plaza vibe) + CREW chat (your clan, the sticky home). Presence roster with green dots (live). The Clan Yard = the crew home (roster + feed + donations + chat + streak + war). Keep it a "place," not a wall of text -- feed cards + reactions > raw scroll. Party/2v2 flow = Phase 3 (realtime).

## 3. MODERATION STACK (cheap, Supabase edge fns, age-appropriate; enforces the BCARDD positive-vibes law)
- Auto-filter: profanity/slur list + the positive-vibes blocklist (no war/tragedy/politics/hate) in ak-chat BEFORE insert (already spec'd) -> reject + soft-warn.
- Rate-limit / slow-mode: per-user send cap in ak-chat (anti-spam/flood).
- Report/block/mute: ak_chat_reports (sink) + ak_chat_bans (escalating: warn -> mute -> temp ban -> ban); block = client-side hide + server mute.
- Trust levels: new accounts slow-moded harder; older/higher-fame loosened.
- Fixed-emoji reactions (no free emoji) = no extra mod surface.
- Human escalation: reports surface to an ops view; AI-toxicity (a cheap model) optional fast-follow.

## 4. PHASING
Phase 2 MVP = Tier 1 (reactions, feed, mentions, streak, notifications) + the moderation stack + World/Crew chat (the staged layer activated). Tier 2 fast-follow. Tier 3 (DMs) + realtime plaza/2v2 = Phase 3. (Full output: task w8wn2jfye.)
