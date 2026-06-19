# ALLEY KINGZ -- SOCIAL LAYER ARCHITECTURE (Build-Ready)
**Status: BUILD-READY MAP. Grounded on the live stack, cheapest-path-first.**
Date: 2026-06-14 | Author: social-layer architect

## GROUND TRUTH (verified against the live code, not assumed)
- Client: vanilla-JS static site on Cloudflare Pages (`alleykingz.online`). No bundler (phone-proot safe).
- Auth + DB: Supabase project **`mfghdobptredxxhbjwyz`**, AK's OWN project + OWN "Alley Kingz" Google OAuth client (per `AUTH_SEPARATION_DOCTRINE.md` -- never route into the casino; redirect glob `https://alleykingz.online/**`).
- Identity: `ak_player_id` = auth uid. Anon key is public-by-design (`window.AK_SUPABASE_ANON_KEY`).
- Save layer: `public.ak_player_saves` -- one jsonb row per user, RLS owner-scoped, newest-wins. (`game/ak_account.js`.)
- Server-authoritative pattern ALREADY PROVEN: `game/shop/shop.js` POSTs INTENTS to edge function `/functions/v1/alley-kingz-shop` with `{action, player_id, ...}` + `apikey`/`Bearer` anon headers; the function is the truth, client never mutates money. **We copy this exact pattern for every social mutation.**
- Wallet/economy: `ak_profile` (localStorage) + `economy.js` (`AK_ECON`); currency = Gems + Gold; cards held as copies/scrap.
- Roster: 106 cards across **4 factions** = the lore houses:
  - `boneguard_crew` (home of **$BCARDD**, card #0001 Mythic = the dealer/coin)
  - `zoomie_syndicate` | `leashbreak_tactix` | `k9_circuitry`
- Always-on host for realtime: **e5-mother** (tailnet ARM box, marginal ~$0) via Cloudflare Tunnel; Railway (~$5-20/mo) is the managed graduate path.
- Combat sim (`engine.js`) uses `Math.random()` everywhere -> **NOT deterministic.** This gates trusted realtime (see Phase 3) but does NOT block Phases 1-2.

Naming: the 4 factions are fixed LORE houses. A player-created group is a **CREW** (a clan). Every Crew picks a faction allegiance -> that drives its crest base + ties straight into the $BCARDD dog-crew lore (a Boneguard Crew aligns under the coin's house).

================================================================
## 1. CREWS / CLANS
================================================================
Pure CRUD + chat. **Zero new infrastructure -- ships on the current Supabase project today.**

### 1.1 Data model (Supabase, `ak_` namespace, RLS owner/crew-scoped)
```sql
-- A crew = a player clan, aligned to one of the 4 lore factions for identity.
create table public.ak_crews (
  id            uuid primary key default gen_random_uuid(),
  name          text not null unique,
  tag           text not null,                 -- 2-4 char crew tag, e.g. "BONE"
  faction       text not null,                 -- boneguard_crew | zoomie_syndicate | leashbreak_tactix | k9_circuitry
  crest         text not null default 'default',-- crest id (faction base + accent)
  description   text default '',
  region        text default '',
  privacy       text not null default 'open',  -- open | request | closed
  req_trophies  int  not null default 0,
  trophies      int  not null default 0,       -- sum/agg of member ladder
  member_count  int  not null default 1,
  donations_week int not null default 0,
  war_wins      int  not null default 0,
  created_by    uuid not null,                 -- auth.uid
  created_at    timestamptz not null default now()
);

create table public.ak_crew_members (
  crew_id        uuid not null references public.ak_crews(id) on delete cascade,
  user_id        uuid not null,                -- auth.uid; UNIQUE -> one crew per player
  role           text not null default 'member',-- leader | co | elder | member
  donated_week   int  not null default 0,
  received_week  int  not null default 0,
  fame_week      int  not null default 0,      -- war contribution this season
  joined_at      timestamptz not null default now(),
  last_seen      timestamptz not null default now(),
  primary key (crew_id, user_id),
  unique (user_id)
);

create table public.ak_crew_requests (              -- request-to-join queue (privacy='request')
  id         uuid primary key default gen_random_uuid(),
  crew_id    uuid not null references public.ak_crews(id) on delete cascade,
  user_id    uuid not null,
  status     text not null default 'pending',   -- pending | accepted | rejected
  created_at timestamptz not null default now(),
  unique (crew_id, user_id)
);
```

### 1.2 Roles (4 tiers, mirrors Clash -- CR-SOCIAL brief)
- **member** -- donate/request cards, chat, play crew wars.
- **elder** -- + invite, kick lower ranks.
- **co** -- + accept/reject requests, promote/demote up to elder, edit crew settings, start war.
- **leader** -- full control; one per crew; can transfer crown / promote a co to leader.

### 1.3 Create / join flow (server-authoritative via `ak-crew` edge fn)
- **Create** = costs **1,000 Gold** (Clash parity). Client -> `ak-crew {action:'create', ...}`; server verifies gold (reads economy), deducts, inserts crew + leader membership atomically. Gate: tutorial complete.
- **Join** -- `open`: instant `ak-crew {action:'join'}` insert (if `member_count < 50` and trophies >= req). `request`: writes `ak_crew_requests`; a leader/co calls `{action:'approve'}`. `closed`: no requests.
- **Cap**: 50 members (Clash parity). **Card-request gate**: King Level 3 (CR parity).
- **Leave/kick/promote/demote**: `ak-crew` actions, role-gated server-side.

### 1.4 Donations -- the "carry your weight" reciprocal loop (top-ROI mechanic per the research brief)
The cheapest, deepest-retention hook: dozens of micro-interactions/day, makes a player's *absence felt*.
```sql
create table public.ak_donation_requests (
  id           uuid primary key default gen_random_uuid(),
  crew_id      uuid not null references public.ak_crews(id) on delete cascade,
  user_id      uuid not null,                  -- requester
  card_id      text not null,
  qty_req      int  not null,
  qty_filled   int  not null default 0,
  expires_at   timestamptz not null,           -- ~3-8h appointment window
  created_at   timestamptz not null default now()
);
create table public.ak_donations (
  id           uuid primary key default gen_random_uuid(),
  crew_id      uuid not null,
  request_id   uuid references public.ak_donation_requests(id) on delete set null,
  donor_id     uuid not null,
  recipient_id uuid not null,
  card_id      text not null,
  qty          int  not null,
  created_at   timestamptz not null default now()
);
```
- Flow: a member posts a request (one open at a time, cooldown). Crewmates **fill** it -> `ak-crew {action:'donate'}`: server grants the recipient card copies, pays the **donor** Gold + crew XP, bumps `donated_week`/`received_week`, increments `ak_crews.donations_week`. Weekly reset (pg_cron Mon 00:00 PT) -> drives a weekly "carry your weight" leaderboard inside the crew.
- Caps server-side: max qty per card by rarity, donor weekly cap, request cooldown. Donations are **in-game value only** (Lane A -- no money rail, brand-safe per retention ethics guardrail).

### 1.5 Crew Wars (recurring shared win-condition + per-member quota -- pattern #2 from the research brief)
Converts "I might log in" into "my crew needs my matches before reset."
```sql
create table public.ak_crew_wars (
  id          uuid primary key default gen_random_uuid(),
  crew_id     uuid not null,
  opp_crew_id uuid,
  season      int  not null,
  state       text not null default 'prep',    -- prep | battle | ended
  score       int  not null default 0,
  opp_score   int  not null default 0,
  tickets     int  not null default 4,         -- per-member match allotment
  starts_at   timestamptz, ends_at timestamptz
);
create table public.ak_war_battles (
  war_id     uuid not null references public.ak_crew_wars(id) on delete cascade,
  user_id    uuid not null,
  result     text not null,                     -- win | loss
  fame       int  not null,
  created_at timestamptz not null default now()
);
```
- A war = the sum of members' battles. Each member gets N tickets/period; tiered crew rewards by final ranking. **War battles REUSE the ghost resolver (Phase 2)** -> wars cost zero realtime infra. Until Phase 2 lands, war = tally of normal ladder wins (still a shared goal + quota).

### 1.6 Crew identity / $BCARDD lore tie-in
- Crest = faction base + accent color/sigil. A Boneguard crew literally flies under the **$BCARDD** house (card #0001). Crew tag shown next to player name in chat + on the ladder.
- Faction allegiance can grant a tiny cosmetic flavor (faction banner in crew home). Keep it cosmetic -- no stat pay-to-win (retention ethics guardrail).

================================================================
## 2. CHAT (Supabase Realtime) -- cheapest to ship, biggest social hook
================================================================
Three Realtime primitives, all in our existing plan, ~$0 at our scale: **Broadcast** (ephemeral pub/sub), **Presence** (online roster), **Postgres Changes** (stream inserts).

### 2.1 Channels
- **World chat** -- one global channel `ak:world`. Presence = global online count + roster.
- **Crew chat** -- per-crew channel `ak:crew:<crew_id>`. Presence = who's online in the crew (green dots, drives the donation loop).
- (Phase 3) **Party** -- ephemeral `ak:party:<id>` for 2v2 invites.

### 2.2 Send/receive pattern (moderatable + cheap -- REALTIME-TECH recommendation)
- **SEND = edge function `ak-chat {action:'send', scope, crew_id?, body}`** so the server can: (a) rate-limit, (b) profanity-filter, (c) ban-check, (d) INSERT the row. Never let clients broadcast raw user text unmoderated.
- **RECEIVE = Supabase Realtime Postgres Changes** on `ak_chat_messages` filtered by `scope`/`crew_id` (RLS scopes crew rows to members). On channel join, the client also fetches the last 50 rows for history (one `select ... order by created_at desc limit 50`).
- **PRESENCE = client-side** `channel.track({user_id, name, faction, crew_tag})` on `ak:world` and `ak:crew:<id>`.

```sql
create table public.ak_chat_messages (
  id         bigint generated always as identity primary key,
  scope      text not null,                      -- world | crew
  crew_id    uuid,                               -- null for world
  user_id    uuid not null,
  name       text not null,
  faction    text,
  body       text not null,
  created_at timestamptz not null default now()
);
create index on public.ak_chat_messages (scope, crew_id, created_at desc);

create table public.ak_chat_bans (
  user_id uuid primary key, until timestamptz, reason text, created_at timestamptz default now()
);
create table public.ak_chat_reports (
  id bigint generated always as identity primary key,
  message_id bigint, reporter_id uuid, reason text, created_at timestamptz default now()
);
```

### 2.3 Rate-limit + profanity (server-side, in `ak-chat`)
- **Rate-limit**: token bucket per user_id -- reject if >1 msg / 2s or >20 / min (count recent rows or an in-memory KV). Client shows a soft "slow down" toast.
- **Profanity**: wordlist filter in the edge function -> mask (`****`) or reject; repeated offenders auto-write `ak_chat_bans` (escalating: 5min -> 1h -> 24h).
- **Length cap**: 200 chars. **Links**: stripped in world chat (anti-spam/scam, matches the $BCARDD "no links in DMs" posture).

### 2.4 Store / retention (memory-pipeline pass per Comms Doctrine -- no raw delete)
- Keep crew chat ~30 days, world chat ~7 days. **pg_cron** nightly prune of aged rows. Per doctrine, an archive copy can be batched before prune for any flagged/reported threads.

================================================================
## 3. 2v2 -- GHOST FIRST, REALTIME LATER
================================================================
Mirrors the locked PvP call (`PVP_CLANS_ARCHITECTURE.md`): static + edge functions can do **async ghost**, not a trusted live referee. So we ship the feel first, earn realtime later.

### 3.1 Phase 2 -- Ghost 2v2 (ships on the current stack, ~$0)
- **You + an AI-piloted ALLY (a crewmate's ghost) vs TWO opponent snapshot decks** (also ghost-piloted by the existing `engine.js` AI). It FEELS like a real tag-team match (real decks, real names, real trophies, real ladder movement) with zero realtime infra.
- Ally preference: a crewmate's ghost (deepens the crew bond); falls back to any trophy-matched ghost.
```sql
create table public.ak_ghosts (                    -- snapshot taken at end of each battle
  user_id    uuid primary key,
  name       text, faction text, trophies int,
  deck       jsonb not null,                       -- the player's real deck
  policy     jsonb,                                -- light play-policy hints for the AI driver
  snapshot_at timestamptz not null default now()
);
create table public.ak_ladder (
  user_id uuid not null, mode text not null,        -- '1v1' | '2v2'
  trophies int default 0, elo int default 1000,
  wins int default 0, losses int default 0, streak int default 0,
  updated_at timestamptz default now(),
  primary key (user_id, mode)
);
create table public.ak_match_history (
  id uuid primary key default gen_random_uuid(),
  mode text not null,                               -- '2v2_ghost' | '2v2_live' | '1v1_ghost' ...
  team_a uuid[] not null, team_b uuid[] not null,
  winner text not null,                             -- 'a' | 'b'
  seed bigint, trophy_delta int, war_id uuid,
  created_at timestamptz default now()
);
```
- Resolve via edge fn **`ak-pvp {action:'resolve_ghost_2v2', match}`**: server sanity-bounds the client-reported result, updates both teams' `ak_ladder`('2v2'), writes `ak_match_history`, and if `war_id` set, writes `ak_war_battles` fame. (Crew wars plug straight in here.)
- **Do the deterministic-RNG refactor here** (route every `Math.random()` in `engine.js` through a seedable mulberry32 off the existing FNV-1a hash). It makes ghost results reproducible AND is the gate to Phase 3.

### 3.2 Phase 3 -- Realtime 2v2 (authoritative server, when concurrency/uptime hurts)
- Stand up a **Deno/Colyseus room server on e5-mother** behind a Cloudflare Tunnel (free, marginal ~$0); graduate to **Railway (~$5-20/mo)** when it hurts.
- Clients send INPUTS (card, lane, time); the server runs the now-deterministic sim and is the **referee**; re-simulation anti-cheat fully on. Supabase Realtime handles lobby/presence/party invites; the match server handles the fight.
- Party = crew-mate taps "Tag Team" in crew chat -> `ak:party:<id>` invite -> both queue together; matchmaking pairs the party vs another party (or two solo-queued + their ghosts).

================================================================
## 4. PHASED PLAN (effort + cost)
================================================================
| Phase | What | Infra | Effort | Cost |
|---|---|---|---|---|
| **1** | **Crews + World/Crew Chat + Donations + Crew-War shell** | Existing Supabase project + Realtime | ~3-5 days | **$0** |
| **2** | **Ghost 2v2 + ladder + crew wars wired to ghost resolver + deterministic-RNG refactor** | Existing stack | ~1-2 weeks | **$0** |
| **3** | **Realtime 2v2** authoritative server | e5-mother + CF Tunnel -> Railway at scale | ~2-4 weeks | ~$0 marginal, ~$5-20/mo at scale |

### Build artifacts per phase
- **Phase 1**: migration `20260614_social_layer.sql` (crews, members, requests, donations, wars, chat, bans, reports + RLS + pg_cron weekly reset/prune); edge fns **`ak-crew`** (create/join/approve/promote/demote/kick/donate/request) + **`ak-chat`** (send w/ rate-limit + profanity + ban). Realtime channels `ak:world`, `ak:crew:<id>`. UI: **Crew tab** + **Chat panel**.
- **Phase 2**: migration adds `ak_ghosts`, `ak_ladder`, `ak_match_history`; edge fn **`ak-pvp`** (snapshot ghost on battle-end, resolve_ghost_2v2); `engine.js` RNG refactor; UI: **2v2 mode tile** + ghost match flow + ladder screen.
- **Phase 3**: Deno/Colyseus server repo (deployed to e5-mother via systemd + CF Tunnel); input-protocol + re-sim validation; party channel; UI: party invite in crew chat + live 2v2 lobby.

### UI surfaces (all vanilla JS, mounted like the existing shop/auth chips)
- **Crew tab** (shield icon in lobby): browse/search/create; crew home = crest, trophies, war banner, roster w/ roles + online dots; **donation board** (open requests + "fill" buttons); settings (role-gated).
- **Chat panel** (slide-up drawer, mounts via a `#ak-chat` node like `#ak-auth`): tabs **World | Crew**, presence roster, 200-char input w/ rate-limit toast, long-press message -> report.
- **2v2 mode tile** on the battle/mode-select screen: "Tag Team (2v2)" -> pick/auto-assign crew ally -> queue (ghost in P2, live in P3).

### Security / doctrine compliance
- Every mutation goes through an edge function (auth + logging boundary), never client-trusted -- same law the shop already follows.
- RLS: a user reads/writes only their crew's rows; role gates kick/promote/start-war/approve server-side.
- Auth separation: AK project + AK OAuth only; redirect glob `https://alleykingz.online/**`. Never touch casino tables.
- Brand-safe: donations + rewards are in-game value only (Lane A); no pay-to-win; chat link-stripping + profanity filter match the $BCARDD positive-vibes posture.

================================================================
## THE ONE OPERATOR DECISION
================================================================
**Approve Phase 1 (Crews + World/Crew Chat + Donations) to ship NOW on the existing Supabase free tier -- $0, ~3-5 days -- with 2v2 deferred to Phases 2-3?**
GO = the biggest retention hook (a social home + the carry-your-weight donation loop + live chat) lands this week on infra we already pay for, zero new ops. The 2v2 build (ghost, then realtime) follows the already-locked PvP sequencing. Everything below branches from this yes.

## THE SINGLE CLEAREST FIRST BUILD STEP
Write + apply Supabase migration **`supabase/migrations/20260614_social_layer.sql`** for the keystone tables **`ak_crews` + `ak_crew_members`** (with owner/crew-scoped RLS and the one-crew-per-player unique), then deploy edge function **`ak-crew`** with `action:'create'` and `action:'join'`. That is the vertical slice that lets a player create a crew and another player join it end-to-end -- chat, donations, and wars all hang off these two tables.
