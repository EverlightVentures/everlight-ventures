# MODULE_04_CREW -- SPEC

**Status:** documented spec + stub. Wraps the STAGED Supabase social layer.
**Owner module dir:** `ALLEY_KINGZ_CORE/MODULE_04_CREW/`
**Primary stub:** `CrewManager.js`

---

## 1. Purpose

MODULE_04_CREW is the social-graph spine of Alley Kingz: it lets players form
crews (clans), talk to each other (world + crew chat), help each other
(reinforcements / card donations), and fight together (crew war + win streak).

It is a **thin, server-authoritative client**. It owns NO source-of-truth state.
Every mutating action is a call to an existing Supabase edge function
(`ak-crew`, `ak-chat`) running with the service role; the client never writes the
DB directly. This mirrors the proven `game/social.js` and `alley-kingz-shop`
patterns: the server is the only writer, the client is a renderer + event emitter.

This module is the **factual layer**. It emits plain facts ("a war started",
"a member left", "a reinforcement was filled"). It does NOT decide what is
urgent, who to shame, or what push to fire -- that is MODULE_05_SOCIAL_URGENCY's
job. MODULE_04 never imports MODULE_05; the only wire between them is the EventBus.

---

## 2. Architecture law (non-negotiable)

- **No module imports another.** `CrewManager.js` imports nothing from CORE and
  is imported by nothing. All cross-module comms go over `window.AK_EventBus`.
- **Server is the only writer.** The client emits intents and renders facts. The
  edge functions enforce gold cost, 50-member cap, one-crew-per-player, role
  gates, rate-limit, profanity, and ban-checks. Trusting the client is a bug.
- **Degrades gracefully signed-out.** Every read returns `{ ok:false }` offline;
  the UI shows a sign-in prompt. No throw ever escapes a bus emit.
- **No em-dashes in code or copy.** Use `--` or `-`. Brand is "Alley Kingz" (Z).

---

## 3. Reuse map -- onto the STAGED Supabase social layer

This module does NOT design new storage. It binds to what is already staged:

| Concern            | Staged asset (already written, awaiting GO)                          |
|--------------------|----------------------------------------------------------------------|
| Crews / roster     | `ak_crews`, `ak_crew_members`, `ak_crew_requests` (migration `20260614000000_social_layer.sql`) |
| Reinforcements     | `ak_donation_requests`, `ak_donations` + grants rail `ak_grants` (`20260614010000_grants_donations.sql`) |
| Crew war           | `ak_crew_wars`, `ak_war_battles`                                      |
| Chat               | `ak_chat_messages`, `ak_chat_bans`, `ak_chat_reports`                |
| Write path         | edge fns `supabase/functions/ak-crew`, `supabase/functions/ak-chat`  |
| Read/live path     | Realtime postgres_changes on `ak_chat_messages`, `ak_crew_members`, `ak_donation_requests` |
| Existing client    | `game/social.js` (self-mounting Crew HQ UI -- CrewManager is the headless brain behind it) |
| Shared SB client   | `AKAccount.client()` (one client, auto-attaches JWT to `functions.invoke`) |

**Relationship to `game/social.js`:** `social.js` is today a monolith that both
renders Crew HQ AND talks to the edge functions. CrewManager is the extraction of
the *data/intent* half into a CORE module that emits facts on the bus. Migration
path is non-breaking: `social.js` can keep its UI and either (a) call CrewManager
methods instead of its private `call()`, or (b) subscribe to CrewManager's bus
events for live updates. CrewManager re-emits the same edge-fn results `social.js`
already consumes, so no schema or edge-fn change is required for v1.

### New columns needed (additive, deferred to migration time)
- `ak_crews.war_streak int not null default 0` -- consecutive crew-war wins (Section 6).
- `ak_crew_members.last_seen` already exists -- reused for online/idle scoring.
No table is created or dropped by this module; only an `ALTER ... ADD COLUMN IF
NOT EXISTS` is required and it is listed here for the migration author, not run here.

---

## 4. Feature: crew create / join / leave

### 4.1 Create
- Inputs: `name` (3-24), `tag` (2-4), `faction` (one of the 4 lore factions),
  `privacy` (`open|request|closed`), `description` (<=200), optional `region`,
  `req_trophies`.
- Server enforces: unique name, tag length, faction enum, one-crew-per-player
  (the `unique(user_id)` constraint on `ak_crew_members`), founder becomes
  `leader`, `member_count=1`.
- Edge call: `ak-crew { action:'create', ... }`.
- Emits on success: `crew.created` then `crew.joined` (self) then `crew.roster.updated`.

### 4.2 Join
- `open` crew -> immediate membership. `request` crew -> row in `ak_crew_requests`
  (`status='pending'`). `closed` -> rejected unless invited.
- Edge call: `ak-crew { action:'join', crew_id }` -> `{ ok, requested? }`.
- Emits: `crew.joined { crewId, userId, requested }` (requested=true means queued).

### 4.3 Leave / kick / promote / demote
- `ak-crew { action:'leave' }`. Leader leaving triggers server-side succession
  (oldest co-leader, else highest trophies). Last member leaving disbands the crew.
- Officer actions (`promote`, `demote`, `kick`) gated by caller role
  (`leader|co`); server rejects under-privileged callers.
- Emits: `crew.left`, `crew.member.promoted`, `crew.member.demoted`,
  `crew.member.kicked`, each followed by `crew.roster.updated`.

### 4.4 Browse / search / mine
- `ak-crew { action:'list', q }` -> directory (RLS lets any authed user browse).
- `ak-crew { action:'mine' }` -> `{ crew, role, members }`; CrewManager caches it.
- Emits: `crew.directory.loaded`, `crew.loaded`.

---

## 5. Feature: chat channels (world + crew)

- Two scopes: `world` (all signed-in players) and `crew` (members only, RLS-scoped).
- **Send** is server-gated: `ak-chat { action:'send', scope, body, name, faction }`.
  Server runs rate-limit + profanity + ban-check (`ak_chat_bans`) and is the only
  writer to `ak_chat_messages`.
- **Receive** is Realtime postgres_changes on `ak_chat_messages`, seeded by
  `ak-chat { action:'history', scope }` (last 50). Crew rows are RLS-scoped so a
  non-member never receives them.
- **Report** -> `ak_chat_reports`; **ban** is service-role only.
- XSS-safe rendering is the UI's job (`mk()` builder, textContent, no innerHTML).
  CrewManager only moves data + emits `crew.chat.message { scope, crewId, userId, name, faction, body, id }`.
- Chat is also the **delivery surface for MODULE_05's social weapons** (betrayal
  log line, MVP callout, flash-bonus banner). MODULE_05 emits an intent; the
  server posts a system message; CrewManager surfaces it like any other message.
  CrewManager itself never authors weaponized copy -- separation of concerns.

---

## 6. Feature: reinforcements (the carry-your-weight loop)

"Reinforcements" = the donation request/fill loop, AK's top retention hook
(mirrors Clash card requests). Free for the donor, a real boost for the receiver,
so every member has a low-friction daily reason to open chat.

- **Request:** `ak-crew { action:'don-request', card_id, qty_req, name }` -> row in
  `ak_donation_requests` with an `expires_at` appointment window (3-8h). Emits
  `crew.reinforcement.requested { crewId, userId, cardId, qtyReq, expiresAt }`.
- **Fill:** `ak-crew { action:'don-fill', request_id }` -> server decrements donor
  stock conceptually, increments `qty_filled`, writes `ak_donations`, queues a
  grant in `ak_grants` for the recipient (claimed client-side via `AK_ECON`).
  Emits `crew.reinforcement.filled { requestId, donorId, recipientId, cardId, qty }`.
- **Weekly reciprocity:** `donated_week` / `received_week` per member drive the
  "who carries their weight" view; reset Monday 08:00 UTC by the staged pg_cron.
- **Grant claim:** on load + on `auth.changed`, CrewManager triggers
  `ak-crew { action:'claim-grants' }` and applies via the economy module, then
  emits `crew.grant.claimed { kinds, totals }`. (Economy application is delegated;
  CrewManager does not own the economy -- it emits and lets MODULE_06_ECONOMY apply.)

**Urgency hook:** an unfilled request nearing `expires_at` is exactly what
MODULE_05 turns into a "shield donation" Tier-3 nudge. CrewManager only emits the
fact + the deadline; it never schedules the nudge.

---

## 7. Feature: crew war + streak

- A war pairs the crew vs an opponent for a `season`; lifecycle `prep -> battle -> ended`
  (`ak_crew_wars.state`). Each member gets `tickets` (default 4) match allotments.
- Until the Phase-2 ghost resolver lands, a war = tally of normal ladder wins:
  `match.win` while `state='battle'` and tickets remain -> `ak_war_battles` row +
  `fame` accrues to `ak_crew_members.fame_week` and `ak_crew_wars.score`.
- CrewManager listens for `match.win` / `match.loss` (emitted by the engine module)
  and forwards a war-contribution intent to `ak-crew { action:'war-report', result }`;
  the server decides if it counts (state, tickets) and returns the new score.
- Emits: `crew.war.started`, `crew.war.scored { score, oppScore, fameDelta, userId }`,
  `crew.war.ended { won, streak }`.
- **Streak:** on a war win the server increments `ak_crews.war_streak`; a loss
  resets it to 0. Emitted as `crew.streak.updated { crewId, streak, broken }`.
  Streak is the fuel for MODULE_05's "streak crisis" tier (don't break the run).

---

## 8. Event contract (this module's bus surface)

### Emits (facts)
| Event | Payload |
|-------|---------|
| `crew.loaded` | `{ crew, role, members }` |
| `crew.directory.loaded` | `{ crews }` |
| `crew.created` | `{ crewId, name, tag, faction, leaderId }` |
| `crew.joined` | `{ crewId, userId, requested }` |
| `crew.left` | `{ crewId, userId, disbanded }` |
| `crew.member.promoted` / `crew.member.demoted` / `crew.member.kicked` | `{ crewId, userId, byUserId, role }` |
| `crew.roster.updated` | `{ crewId, members }` |
| `crew.chat.message` | `{ id, scope, crewId, userId, name, faction, body, at }` |
| `crew.reinforcement.requested` | `{ requestId, crewId, userId, cardId, qtyReq, expiresAt }` |
| `crew.reinforcement.filled` | `{ requestId, donorId, recipientId, cardId, qty }` |
| `crew.grant.claimed` | `{ kinds, totals }` |
| `crew.war.started` | `{ warId, crewId, oppCrewId, season, endsAt, tickets }` |
| `crew.war.scored` | `{ warId, score, oppScore, fameDelta, userId }` |
| `crew.war.ended` | `{ warId, won, streak }` |
| `crew.streak.updated` | `{ crewId, streak, broken }` |
| `crew.error` | `{ action, error }` |

### Listens (intents / upstream facts)
| Event | Reaction |
|-------|----------|
| `auth.changed` | refresh `mine`, claim grants, re-subscribe Realtime |
| `config.ready` | read endpoints / feature flags (e.g. war enabled) |
| `match.win` / `match.loss` | forward war contribution + quest event when in an active war |
| `crew.request.*` (UI intents) | call the matching `ak-crew` action |

---

## 9. Public API (CrewManager.js)

```
CrewManager.attach(bus, opts)        // wire bus listeners + Realtime; idempotent
CrewManager.create(spec)             // -> Promise<{ok, crew}>
CrewManager.join(crewId)             // -> Promise<{ok, requested}>
CrewManager.leave()                  // -> Promise<{ok}>
CrewManager.list(query)              // -> Promise<{ok, crews}>
CrewManager.mine()                   // -> Promise<{ok, crew, role, members}>
CrewManager.sendChat(scope, body)    // -> Promise<{ok, message}>
CrewManager.requestReinforcement(cardId, qty)  // -> Promise<{ok}>
CrewManager.fillReinforcement(requestId)        // -> Promise<{ok, filled}>
CrewManager.reportWarResult(result)  // -> Promise<{ok, score}>
CrewManager.state()                  // synchronous snapshot of cached crew/role/members
```

All async methods resolve `{ ok:false, error }` rather than throwing, and emit the
matching `crew.*` fact on success / `crew.error` on failure.

---

## 10. Out of scope (handled elsewhere)

- **Urgency, push, shaming, countdowns, reward-flow** -> MODULE_05_SOCIAL_URGENCY.
- **Economy mutation (applying a grant to cards/gold)** -> MODULE_06_ECONOMY.
- **Card / battle rules** -> the engine module.
- **DB writes + business rules** -> the `ak-crew` / `ak-chat` edge functions.
- **Realtime 2v2 war resolution** -> Phase 3 (separate; this module ships the
  ladder-tally war shell the staged schema supports today).
