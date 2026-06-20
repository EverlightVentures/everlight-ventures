# MODULE_05_SOCIAL_URGENCY -- SPEC

**Codename:** the socially-radioactive engine.
**Status:** documented spec + stub.
**Owner module dir:** `ALLEY_KINGZ_CORE/MODULE_05_SOCIAL_URGENCY/`
**Primary stub:** `PushNotificationManager.js`

---

## 1. Purpose

MODULE_04_CREW produces cold facts ("a war started", "a member left", "a streak
hit 7"). MODULE_05 is the layer that makes those facts **matter right now**. It is
the retention engine: it scores facts for urgency, fires the right nudge on the
right channel at the right second, and wires the crew's social graph into a
dopamine loop that keeps players coming back and pulling each other back.

It does this three ways:

1. **3-tier urgency** -- a scoring + scheduling brain that turns crew/war/streak
   state into time-boxed calls to action (siege push, war countdown, streak
   crisis, revenge, shield donation).
2. **Crew chat as a weapon** -- it turns the chat channel from a talk surface into
   a pressure surface (betrayal log, MVP spotlight/laggard nudge, crew chest,
   flash bonus, rival tagging).
3. **The Reward-Flow loop** -- an anticipation -> action -> reward -> share cycle
   that closes back on itself so every reward seeds the next anticipation.

It imports nothing and is imported by nothing. It learns everything by listening
to `crew.*`, `match.*`, and `auth.*` on the EventBus, and it acts by (a) emitting
`urgency.*` / `social.weapon.*` / `rewardflow.*` facts and (b) delivering pushes
through `PushNotificationManager`.

**Brand guardrail (HARD).** AK / $BCARDD doctrine is "attention, not tension."
This engine creates *competitive* pressure, never *abusive* pressure. "Shaming"
here means a light, opt-out-friendly spotlight on the laggard ("Rex carried 40
cards this week -- the rest of us owe him"), never harassment, never a personal
attack, never anything a player cannot mute. Every weaponized line is
server-authored, rate-limited, mutable, and configurable; the engine ships with a
`tone` flag (`hype | competitive | off`) defaulting to `hype`.

---

## 2. Architecture law (non-negotiable)

- **No module imports another.** Only wire is `window.AK_EventBus`.
- **It reacts, it does not own.** It never writes the crew DB; when it wants a
  chat line posted it emits `social.weapon.fired` and the crew/edge layer posts a
  system message. When it wants a grant given it emits `urgency.reward.grant` and
  MODULE_06_ECONOMY / the grants rail applies it.
- **Push is best-effort + permissioned.** A blocked/denied notification permission
  is a normal state, never an error. In-app urgency (banners, badges) always works
  even when OS push is denied.
- **No PII to a public surface.** Pushes carry crew/handle only, never email.
  (Consistent with the workspace PII-not-to-public-CDN rule.)
- **No em-dashes. Brand is "Alley Kingz" (Z).**

---

## 3. Reuse map -- onto the STAGED Supabase social layer

The staged layer (migration `20260614000000_social_layer.sql` + `game/social.js`)
gives us live state + a delivery surface; MODULE_05 reads it and adds the *push
transport* + the *urgency brain*, neither of which exists yet.

| Urgency signal     | Source it reads (already staged)                                        |
|--------------------|-------------------------------------------------------------------------|
| War countdown      | `ak_crew_wars.ends_at`, `.state`, `.tickets`, `.score/.opp_score`       |
| Siege push         | `ak_crew_wars` score swing + `ak_war_battles` inflow (close + final hr) |
| Streak crisis      | `ak_crews.war_streak` (additive col) + war loss risk                    |
| Shield donation    | `ak_donation_requests.expires_at` approaching with `qty_filled<qty_req` |
| MVP / laggard      | `ak_crew_members.donated_week / received_week / fame_week`              |
| Betrayal log       | `crew.left` during `state='battle'`; member with 0 `donated_week`       |
| Crew chest         | aggregate of donations + war fame this week (derived, no new table req) |
| Rival tagging      | `ak_crews` directory + `ak_crew_wars.opp_crew_id`                       |
| Delivery surface   | `ak_chat_messages` (system author) via `ak-chat`; Realtime fan-out      |
| Reward grant       | `ak_grants` rail (`20260614010000_grants_donations.sql`)                |

**What MODULE_05 adds that the staged layer does NOT have yet:**
- A **push transport**: Web Push (VAPID) via a service worker for installed/PWA
  players, with a graceful fall-back ladder (Web Push -> in-app banner -> chat
  system message -> next-open badge). FCM/native is a later swap behind the same
  `PushNotificationManager` interface.
- A **subscriptions table** (deferred migration): `ak_push_subscriptions
  (user_id, endpoint, p256dh, auth, platform, created_at, last_ok)` so the server
  side (a future `ak-push` edge fn) can fan out server-timed pushes (war final
  hour) even when the app is closed. v1 client-side only schedules local
  notifications while the tab is alive; the table is specced here for the author.
- A **quiet-hours + frequency cap** policy (Section 7) so the engine is sticky,
  not spammy.

---

## 4. The 3-tier urgency model

Every urgency signal is classified into one of three tiers. Tier sets the channel,
the loudness, and the frequency budget.

### Tier 1 -- SIEGE (interrupt-now)
The crew's shared outcome is on the line in real time. Highest loudness, allowed
to OS-push and break quiet hours (once).
- **Siege push:** crew war is close (`|score - oppScore| <= swing`) AND inside the
  final window (`ends_at - now <= siegeWindow`, default 60 min). CTA: "Final hour.
  We're up 2. Play your tickets NOW."
- Emits `urgency.raised { tier:1, kind:'siege', crewId, warId, deadline, cta }`.

### Tier 2 -- COUNTDOWN (time-boxed, scheduled)
A deadline is coming and the player has unspent agency. Medium loudness, OS-push
allowed inside waking hours, deduped to 1-2 fires per window.
- **War countdown:** `state='battle'`, player has tickets left, `ends_at` within
  the reminder ladder (e.g. T-6h, T-1h). CTA: "War ends in 1h. You have 3 tickets."
- Emits `urgency.raised { tier:2, kind:'war_countdown', deadline, ticketsLeft, cta }`.

### Tier 3 -- NUDGE (ambient, in-app first)
Low-stakes, high-frequency hooks that drive the daily loop. In-app banner / badge
by default; OS-push only if the player has been away > `awayThreshold`.
- **Streak crisis:** `war_streak >= 3` and a loss/inaction would break it. CTA:
  "7-war streak on the line. Don't be the one who breaks it."
- **Revenge:** player just lost a ladder match (or the crew lost a war) -> a
  revenge target is captured. CTA: "Run it back on <opp>." (Frames a loss as a
  reason to return, the single strongest re-engagement hook.)
- **Shield donation:** a crewmate's `ak_donation_requests` row is expiring unfilled.
  CTA: "Maya's request expires in 40m -- cover her." (Free for donor, builds the
  reciprocity debt that powers Section 6.)
- Emits `urgency.raised { tier:3, kind:'streak_crisis'|'revenge'|'shield', ... }`.

Each `urgency.raised` is later resolved with `urgency.cleared { kind, reason }`
when the deadline passes, the action is taken, or the state changes (war ends,
request filled). Cleared urgencies stop their reminder ladder immediately.

---

## 5. Urgency scoring + scheduling

- Each signal gets a **score** = `f(tier, stakes, deadline_proximity, player_agency,
  recency)`. Agency matters: a war the player can still affect outranks a war they
  cannot. A signal with no remaining agency is suppressed.
- **One push per scoring tick wins.** When several signals are live, the engine
  fires only the single highest-scoring one per channel per window, so the player
  never gets a burst. The rest stay queued and re-score next tick.
- **Reminder ladders** are deadline-relative (T-6h / T-1h / T-10m), not wall-clock,
  so they track each war/request individually.
- Scheduling is driven by a single `tick()` (called on bus events + a low-frequency
  timer), never a per-signal timer swarm. Idempotent: re-evaluating the same state
  produces the same decision.

---

## 6. Crew chat as a weapon

The chat channel (`ak_chat_messages`, crew scope) is the highest-attention surface
in the game. MODULE_05 injects *server-authored system messages* into it to convert
attention into action. The engine emits an intent; the crew/edge layer authors and
posts the line; CrewManager surfaces it as a normal message. The engine never
writes chat directly and never authors free-text from the client.

| Weapon | Trigger | System line (tone=hype default) | Guardrail |
|--------|---------|----------------------------------|-----------|
| **Betrayal log** | member leaves while `state='battle'`, or ends week with 0 donations after receiving | "Tank bailed mid-war. Crew remembers." | Factual event only, never an insult; opt-out via `tone=off`; rate-limited 1/event |
| **MVP spotlight + laggard nudge** | weekly: top + bottom by `fame_week`/`donated_week` | "MVP: Rex (52 cards). Bottom 3, your crew needs you." | Praise is named; nudge is grouped/anonymous-by-default, never a personal pile-on |
| **Crew chest** | derived progress bar fills as the crew donates / wins war fame | "Crew Chest 80% -- 6 more wins unlocks it for everyone." | Shared reward, positive-sum; no shame |
| **Flash bonus** | engine opens a short multiplier window (e.g. 2x war fame for 30 min) | "FLASH: 2x war fame for 30 min. Strike now." | Server-gated window; never pay-to-win; gems stay non-cashable |
| **Rival tagging** | a crew @-tags another in world chat / a war is queued vs opp | "Zoomie Syndicate called us out. War in 24h." | Consensual rivalry, blockable; no targeting of individuals |

- Emits `social.weapon.fired { kind, crewId, subjectId?, targetCrewId?, payload }`.
- All weapons honor the `tone` flag and a per-crew weekly cap so chat stays a
  weapon, not a firehose.

---

## 7. Delivery, permissions, and anti-spam (PushNotificationManager)

`PushNotificationManager` is the transport. The urgency brain decides *what* and
*when*; the manager decides *how it reaches the device* and enforces the budget.

**Channel ladder (best-effort, degrades down):**
1. **Web Push** (VAPID + service worker) -- works app-closed once a subscription
   exists and the server `ak-push` fn is live. v1: local `Notification` while tab
   is open.
2. **In-app banner / toast** -- always available; primary for Tier 3.
3. **Chat system message** -- the weapon surface (Section 6).
4. **Next-open badge** -- a count on the crew button for anything missed.

**Permission states:** `default | granted | denied | unsupported`. Asking is
deferred until the player has felt value (after first crew join / first donation),
never on cold load. Denied is a permanent in-app-only mode, not an error.

**Anti-spam policy (sticky, not spammy):**
- **Quiet hours:** default 22:00-08:00 local; only a single Tier-1 siege may break
  them, and at most once per war.
- **Frequency cap:** per-tier daily budget (e.g. T1: 2, T2: 3, T3: 4) + a global
  cap; over-budget signals downgrade to in-app/badge instead of OS push.
- **Coalescing:** multiple live signals collapse to the one highest score per
  window (Section 5).
- **Per-player mute / tone:** `tone=off` silences weapons; per-kind mutes persist.

**API surface (PushNotificationManager.js):**
```
PushNotificationManager.attach(bus, opts)   // wire bus + register SW; idempotent
PushNotificationManager.requestPermission()  // -> Promise<'granted'|'denied'|...>
PushNotificationManager.permission()          // synchronous current state
PushNotificationManager.deliver(notice)        // route a notice down the channel ladder
PushNotificationManager.subscribe()            // -> Promise<subscription|null> (Web Push)
PushNotificationManager.mute(kind, on)          // per-kind opt-out
PushNotificationManager.setQuietHours(start,end)
PushNotificationManager.setTone(tone)           // hype | competitive | off
```
Every `deliver()` emits `push.queued` then `push.sent` / `push.suppressed` /
`push.failed` so the loop (Section 8) and analytics can observe outcomes.

---

## 8. The Reward-Flow dopamine loop

The engine ties the above into a closed four-phase cycle. Each phase emits
`rewardflow.tick { phase, kind, crewId }` so the UI can animate it and analytics
can measure drop-off per phase.

1. **ANTICIPATION** -- a deadline/chest/streak is surfaced (urgency raised). The
   player knows a reward is reachable. (`urgency.raised` -> `rewardflow.tick:anticipation`)
2. **ACTION** -- the player plays the ticket / fills the request / sends the rally.
   (`match.win`, `crew.reinforcement.filled` -> `rewardflow.tick:action`)
3. **REWARD** -- visible payoff: grant via `ak_grants`, chest fill, streak +1, MVP
   crown. Emits `urgency.reward.grant { userId, kind, amount }` for the economy
   rail to apply, and `rewardflow.tick:reward`.
4. **SHARE** -- the reward is broadcast to chat ("Rex closed the war -- streak 8")
   which becomes the **next player's anticipation**. (`social.weapon.fired` ->
   `rewardflow.tick:share`)

The share phase is what makes it *social* radioactivity: one player's reward is the
trigger for the crew's next pull. The loop never dead-ends -- every reward seeds an
anticipation for someone else. Variable-ratio reward sizing (most grants small,
rare big) keeps the loop pulling without becoming predictable, and the brand
guardrail keeps it pull-not-pressure.

---

## 9. Event contract (this module's bus surface)

### Emits
| Event | Payload |
|-------|---------|
| `urgency.raised` | `{ tier, kind, crewId, warId?, deadline?, cta, score }` |
| `urgency.cleared` | `{ kind, crewId, reason }` |
| `urgency.reward.grant` | `{ userId, kind, amount, source:'rewardflow' }` |
| `social.weapon.fired` | `{ kind, crewId, subjectId?, targetCrewId?, payload }` |
| `rewardflow.tick` | `{ phase, kind, crewId }` |
| `push.queued` / `push.sent` / `push.suppressed` / `push.failed` | `{ channel, kind, title, reason? }` |
| `push.permission.changed` | `{ state }` |

### Listens
| Event | Reaction |
|-------|----------|
| `crew.war.started` | open countdown ladder; arm siege watch |
| `crew.war.scored` | re-score siege (closeness); maybe Tier-1 |
| `crew.war.ended` | clear war urgencies; reward/share phase; streak check |
| `crew.streak.updated` | arm/clear streak-crisis; share on milestone |
| `crew.left` | betrayal-log weapon if war active |
| `crew.reinforcement.requested` | arm shield-donation deadline ladder |
| `crew.reinforcement.filled` | clear shield urgency; action->reward->share phases |
| `match.loss` | capture revenge target (Tier 3) |
| `match.win` | action phase; clear revenge if it was the target |
| `auth.changed` | (re)evaluate permission prompt timing; reset budgets per user |
| `config.ready` | read VAPID key, windows, caps, default tone, feature flags |

---

## 10. Out of scope (handled elsewhere)

- **Crew/war/chat/donation facts + DB writes** -> MODULE_04_CREW + `ak-crew`/`ak-chat`.
- **Applying a reward grant to the wallet** -> MODULE_06_ECONOMY (this module only
  emits the grant intent; the economy owns the mutation).
- **Authoring the literal chat copy** -> the crew/edge layer (server-authored,
  brand-checked); this module emits the weapon intent + kind only.
- **Server-timed push while app is fully closed** -> a future `ak-push` edge fn +
  the `ak_push_subscriptions` table specced in Section 3 (deferred migration). v1
  is client/Realtime-driven while the app is reachable.
