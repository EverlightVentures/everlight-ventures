# ALLEY KINGZ -- PvP + CLANS ARCHITECTURE (Phase 4)
**Status: DESIGN ONLY. Zero code, zero spend. Honest engineering, cheapest-path-first.**
Ground truth: static client on Cloudflare Pages (alleykingz.online), data + auth on Supabase
`mfghdobptredxxhbjwyz` (accounts live, `ak_player_saves` = 1 jsonb row/user), server logic in
Supabase Deno edge functions, e5-mother (tailnet ARM box) available as an always-on host,
106-card roster. **Critical fact: the combat sim in `game/engine.js` uses `Math.random()`
everywhere (energy ticks, dodge rolls, loot, jitter). It is NOT deterministic.** Read that twice
before reading the rest -- it shapes every option below.

================================================================
## 1. WHY STATIC HOSTING CANNOT DO AUTHORITATIVE REALTIME ALONE
================================================================
Cloudflare Pages serves static files. There is no long-lived process, no socket you own, no place
to run the battle simulation as the single source of truth. Two browsers can talk (via a relay),
but nobody is the referee. With the current client-sim, "PvP" would mean each client runs its OWN
fight and trusts the other -- which is the exact thing cheaters exploit (edit memory, send "I won").
Authoritative realtime needs a **server process that owns the match state and runs the sim itself**.
Pages cannot be that process. Edge functions are stateless and short-lived (good for request/reply,
bad for a 90-second tick loop holding live state). So: static + edge-functions gets us async and
presence; it cannot get us a trusted live referee. That referee must live somewhere persistent.

================================================================
## 2. SERVER OPTIONS -- REAL TRADEOFFS + ROUGH COST
================================================================
**A) Supabase Realtime (Presence + Broadcast).** Already in our stack, ~free at our scale.
Gives: who's online, lobby chat, "opponent placed a card" message relay, clan chat, live
leaderboards via Postgres changes. Does NOT give: an authoritative simulation. It is a message bus,
not a referee. Perfect for clans/lobby/spectate signalling; useless as anti-cheat on its own.
Cost: included in current plan; Realtime concurrency limits are generous for our size.

**B) Small authoritative match server (Colyseus / Deno on e5-mother).** A Node or Deno process
holding room state, running the sim at a fixed tickrate, clients send only inputs. This is the
real answer for trusted realtime. e5-mother is already paid for and always-on (tailnet ARM box),
so **marginal cost ~$0** -- BUT it is tailnet-only and a single box. To serve public players we
must expose a port via Cloudflare Tunnel (free) and accept: single point of failure, ARM CPU
ceiling (fine for dozens of concurrent matches, not thousands), and our own ops burden (process
manager, restarts, deploys). Railway is the managed alternative: ~$5-20/mo, public by default,
auto-restart, easy deploy, scales with a slider -- you pay to delete the ops headache. **Verdict:
prototype realtime on e5-mother (free), graduate to Railway when concurrency or uptime actually
hurts.** Either way the sim must first be made deterministic (see section 3).

**C) Serverless tick (edge function called on a timer / per-input).** Tempting because it is "in
our stack," but it fights the model: edge functions are stateless, cold-start, and billed per
invocation. Driving a 20Hz tick loop through them means state in Postgres every tick = latency +
cost spike + race conditions. Workable ONLY for slow async turn resolution (see ghost-PvP below),
never for live realtime. Cost: cheap for occasional calls, ugly and slow if abused as a game loop.

================================================================
## 3. ANTI-CHEAT = SERVER-AUTHORITATIVE RESOLUTION
================================================================
Today the client runs the whole fight and would just report the result. A modified client can
report any result. **The fix is the standard one: client sends INPUTS (which card, where, when);
the server runs the sim and produces the OUTCOME.** Client renders a prediction for feel; server
is truth; on mismatch the server wins.
Hard prerequisite: **the sim must be deterministic.** Same inputs + same seed = same result on
every machine. Right now `Math.random()` breaks that -- we must swap it for a seeded PRNG (we
already have a deterministic FNV-1a hash in engine.js; extend it to a seedable mulberry32-style
RNG and route ALL combat randomness through it). Once deterministic, two payoffs: (a) the server
can re-run a match from `seed + input-log` and validate the client's claim cheaply, and (b) ghost
replays (section 6) become exact and reproducible. **This RNG refactor is the single highest-
leverage piece of work and it benefits BOTH phases.** It is the gate to everything trusted.

================================================================
## 4. MATCHMAKING + ELO / TROPHY LADDER
================================================================
Trophies (Clash-style) for the player-facing ladder; a hidden ELO/Glicko rating for fair
matching. On `find_match`: bucket by trophy range, widen the range every few seconds of waiting,
fall back to a bot or a ghost (section 6) if no human appears in ~10-15s (never leave a player
staring at a spinner). Win: +trophies + ELO up; loss: -trophies (floored per arena) + ELO down.
Data on Supabase:
- `ak_ladder(user_id pk, trophies int, elo int, arena int, wins int, losses int, streak int, updated_at)`
- `ak_match_history(id, a_user, b_user, winner, mode, seed, input_log jsonb, trophy_delta, created_at)`
Matchmaking logic = an edge function (`find_match`) writing to a `match_queue` table; the match
server (or ghost resolver) claims the pairing. ELO math is server-side only so clients cannot forge
rating. Leaderboards = a Postgres view ordered by trophies, read live via Supabase Realtime.

================================================================
## 5. CLANS + CLAN-WARS DATA MODEL (Supabase)
================================================================
Pure CRUD + chat -- needs ZERO realtime sim, ships entirely on the current stack.
- `ak_clans(id, name uniq, tag, crest, description, trophies int, member_count, created_by, created_at)`
- `ak_clan_members(clan_id, user_id, role ['leader'|'co'|'elder'|'member'], joined_at, donated_week int, pk(clan_id,user_id))`
- `ak_clan_wars(id, clan_id, opponent_clan_id, season int, state ['prep'|'battle'|'ended'], score_a, score_b, starts_at, ends_at)`
- `ak_clan_war_battles(war_id, user_id, result, fame int, created_at)` -- a war = sum of members' ghost/PvP battles.
- `ak_clan_chat(clan_id, user_id, body, created_at)` -- live via Supabase Realtime broadcast.
Row-Level Security: a user reads/writes only their clan's rows; role gates kick/promote/start-war.
Clan wars deliberately reuse the **ghost-PvP** resolver so war battles cost no realtime infra.

================================================================
## 6. THE PHASED PLAN
================================================================
**PHASE 1 -- ASYNC "GHOST" PvP (ships on the CURRENT stack, ~$0, weeks not months).**
When a player finishes a battle, snapshot their deck + a light "play policy" into Supabase
(`ak_ghosts(user_id, deck jsonb, policy jsonb, trophies, snapshot_at)`). To "PvP," a player is
matched against another player's GHOST: the existing AI drives the opponent's real deck, locally,
in the client. It FEELS like fighting a real person (real deck, real name, real trophies, real
ladder movement) with zero realtime infra. Result posts to an edge function that updates both
players' trophies/ELO; the loser sees "you were raided by X" asynchronously (Clash-style).
This delivers: a real PvP feel, a live leaderboard, clans + clan-wars (war battles = ghost
battles), daily reasons to return -- all on static + Supabase we already run.
*Do the deterministic-RNG refactor (section 3) DURING Phase 1* so ghost results are reproducible
and Phase 2 is a smaller leap. Anti-cheat in Phase 1 is lighter (results are server-recorded and
sanity-bounded, not yet fully re-simulated) -- acceptable because nothing real-money is on the line.

**PHASE 2 -- REALTIME PvP (the obsession loop).** Stand up the authoritative match server
(e5-mother first via Cloudflare Tunnel, Railway when it hurts). Clients send inputs, server runs
the now-deterministic sim and is the referee. Supabase Realtime handles lobby/presence/chat;
the match server handles the fight. Re-simulation anti-cheat goes fully on. Live 1v1, then 2v2,
tournaments, spectate.

================================================================
## RECOMMENDATION -- CHEAPEST PATH TO A PvP FEEL
================================================================
**Ghost-PvP first.** It converts the single-player toy into something with rivals, a ladder, and
clans on infrastructure we already pay for, in a fraction of the time, with no new ops burden. It
also de-risks realtime by forcing the deterministic-RNG work early. Realtime is the better game,
but it is the bigger, costlier, ops-heavier build -- earn the right to it by proving the ladder +
clans + retention loop work with ghosts first. Players cannot tell the difference at the start;
the difference is your burn rate and your timeline.

================================================================
## THE ONE OPERATOR DECISION
================================================================
**Ghost-PvP-first (recommended) -- OR -- jump straight to realtime?**
GO ghost-first = a PvP feel + ladder + clans in weeks on the existing stack, ~$0, deterministic-RNG
refactor done along the way. Jump-to-realtime = the real thing sooner, but a match server, the RNG
refactor, AND anti-cheat all up front, with ongoing ops + likely Railway spend before a single
player benefits. Pick one. Everything in Phase 4 branches from this call.
