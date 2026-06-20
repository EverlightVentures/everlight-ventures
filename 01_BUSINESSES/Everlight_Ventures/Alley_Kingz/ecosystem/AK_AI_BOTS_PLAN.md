# ALLEY KINGZ -- "LIVING WORLD" via AI BOTS (research-backed plan, 2026-06-20)
> Operator: "someone made an AI WoW server with 1800 real bots using DeepSeek -- this is kinda what I'm trying to do." This doc = what they actually did + how it adapts to AK. Companion to AK_LIVING_WORLD.md + AK_RAID_DEFENSE_SYSTEM.md + AK_SYSTEMS_DESIGN.md.

## THE TRUTH ABOUT THE "1800 AI BOTS" (the myth-buster)
The viral WoW build = **AzerothCore** (open-source WotLK emulator) + **mod-playerbots** (a behavior-tree/FSM bot module) + **DeepSeek via an async Ollama bridge** (mod-LLM-Chatter pattern). The headline is misleading ON PURPOSE:
- **The LLM does ALMOST NOTHING.** Movement, pathfinding, questing, combat, raids = 100% the deterministic C++ engine + a simple FSM over in-game variables. ZERO LLM tokens on gameplay.
- **The LLM is bolted on ONLY for chat/flavor** -- ambient barks, party banter, combat callouts. It runs in a SEPARATE async bridge: the server writes a request row -> the bridge answers async -> picked up next tick. The sim NEVER blocks on the LLM; if the LLM is down, yesterday's lines serve.
- **Population scale is DECOUPLED from LLM scale.** 100 bots or 1800 bots read from the SAME flavor pool. Adding bots costs $0 in tokens. DeepSeek is the cheapest serious model (~$0.14/1M in, $0.28/1M out, 90% cache discount); chat is rare vs the per-tick sim, so spend stays tiny. Bottleneck = engine CPU/RAM, NOT the AI.
ONE LINE: **Deterministic engine = the world. Behavior tree = what bots DO. LLM = only what bots SAY, generated async + cached, never on the hot path.**

## AK MAPPING (we already have the equivalents -- NO rebuild)
| Their stack | AK equivalent (in code) |
|---|---|
| AzerothCore (world sim) | `engine.js` (the battler sim) |
| mod-playerbots FSM | `engine.js updateAI(dt)` + `computeAiCurve()` -- already a difficulty-scaled FSM picking cards/lanes. THIS IS THE BEHAVIOR TREE. It exists. |
| bots that resemble real players | `ak_ghosts` (snapshot of a real player's deck + policy) -- designed in SOCIAL_LAYER_ARCHITECTURE Phase 2 |
| Ollama->DeepSeek async chat bridge | a new Supabase edge fn `ak-flavor` + a nightly batch generator on e5-mother |

## THE HARD LINE -- LLM-worth-it vs NEVER
- LLM (flavor, batch-generated, sampled at runtime): bot/crew TAUNTS + victory/defeat barks; rival-base OWNER personas (1-line bio + a few barks); crew-AI strategy CHATTER (cosmetic color); dynamic-event flavor ("the strays are restless tonight..."); wandering NPC-dog one-liners; capped live "hero-moment" lines (boss kill / raid on YOUR base / leaderboard flip).
- NEVER LLM (deterministic engine): card-play decisions (`updateAI`), movement/pathfinding/joystick, combat resolution/damage/raids, night-wave spawning/targeting, matchmaking/trophy/loot, ANYTHING that touches game state, balance, or money.
RULE: if it changes a number in the DB it's deterministic; if it's a string a human reads for vibe it's a sampled (occasionally LLM-generated) flavor line.

## SNAPSHOT-AS-BOT (the cleanest steal = the world-map layer)
On session end, snapshot a real player's deck + base loadout + name + faction + trophy band into `ak_ghosts` + a new `ak_bot_bases`. On the world map (AK_LIVING_WORLD V2 "leave base -> see other bases"), when a trophy band lacks live players, SPAWN bot bases from these snapshots, trophy-matched. The attacker fights a ghost-piloted defense via `engine.js` -- zero realtime infra, zero LLM in the fight. The LLM only ever wrote the owner's bio + 3 taunts (from the pool). Night PvE waves = pure deterministic spawners; LLM writes only the intro line.

## COST MATH (the runaway vs the fix)
- WRONG (call LLM per utterance): 1000 bots x 1 line/min x 4h = 240k lines ~ $3-8/evening, scales with population, unbounded. If on a per-tick mistake: ~$100+/evening.
- RIGHT (batch a pool, sample at runtime): nightly batch = 50 personas x 300 lines = 15k lines ~ **$0.25**, regenerate weekly ~ **$1-4/MONTH FLAT** regardless of bot count. Runtime read = $0/utterance. Optional live "hero-moment" calls hard-capped (~200/day server-wide ~ $0.10/day), fall back to the pool past the cap. **100 or 1000 bots both cost ~$1-4/mo** because tokens are decoupled from concurrency.

## BUILD ORDER (each ships independently, $0-$4/mo)
1. `ak_flavor_pool(persona, line, tag)` table + nightly batch generator (e5-mother cron, NOT the dead phone cron; prefer local Ollama for $0, DeepSeek API for higher quality). Pure content, no gameplay risk.
2. `bot.say()` runtime hook -> wandering NPC dogs + bot opponents + night-wave intros render pooled lines as speech bubbles on the hub. Instant "alive" feel, $0 runtime.
3. `ak_bot_bases` + snapshot-as-bot on the world map -> rival bases that resemble real players, fought via existing `engine.js`/`ak_ghosts`. The CoC world-map layer.
4. Capped live `ak-flavor` hero-moments -> reactive taunts on boss kills / raids on your base / leaderboard flips. Optional spice, bounded cost.

## STACK + GUARDRAILS
- Supabase `mfghdobptredxxhbjwyz` (NOT jdqqmsmwmbsnlnstyavl): one migration adds `ak_flavor_pool` + `ak_bot_bases`, extends `ak_ghosts`. RLS read-only/anon (same posture as existing). Edge fn `ak-flavor` alongside the existing `ak-crew/ak-chat/ak-pass/ak-quests/ak-cosmetics` (server-authoritative INTENT pattern).
- CRYPTO: bots + flavor are pure cosmetic/soft. No bot action mints/awards/prices in $BCARDD/ALK (consistent w/ the AK_RAID_DEFENSE crypto gate). Bot bases give the SAME soft rewards (gold/gems/fragments). Hard LLM budget ceiling in `ak-flavor` (daily server-wide counter -> over cap = serve pool); runtime never calls the LLM directly so the runaway is structurally impossible.
- CONTENT: archetype seeds only, no PII/real-player text to the model; route generation through the `content_engine.py` blocklist posture ($BCARDD positive-vibes law).

## SOURCES
AzerothCore, mod-playerbots (github.com/mod-playerbots/mod-playerbots + DeepWiki), mod-LLM-Chatter (AzerothCore discussion #25107), DeepSeek pricing (NxCode/CloudZero), Blizzard forum "New AI-powered bots". Builder's exact Reddit handle/repo not recoverable (X paywalled, Reddit rate-limited) -- but the load-bearing stack is all public + cited. Full agent findings in the run transcript.
