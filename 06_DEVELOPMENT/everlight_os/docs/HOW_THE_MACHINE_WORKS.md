# How The Machine Works
### Your automation, the Hive, the servers, the site, the devices -- and how they all serve the gameplan

*Plain English. Brought back to Earth. Updated 2026-05-22 by Lucrex.*
*Companion to the gameplan spine: `01_BUSINESSES/Everlight_Ventures/Wealth_OS/00_MASTER_GAMEPLAN.md`.*

---

## The one-sentence version

You are one person, currently couch-hopping and showering at Planet Fitness, running
what looks like a company with a 40-person team -- because the machine does the work of
the team. Its single job right now: **produce wholesale cash, get you into a house-hack,
get you housed and stable.** Everything else is later.

---

## The pieces, and what each one actually does

### 1. You + the phone = the cockpit
The phone (Termux) is where you sit and drive. It is the **control plane** and the
**source of truth for the workspace** -- but it is NOT a server. Edits start here, you
talk to me (Lucrex), I dispatch the Hive. If the phone dies, nothing production stops,
because the servers keep running. Your job is to steer, decide, and close. The machine's
job is everything else.

### 2. The Hive = your workforce
42-plus named agents (Marcus the orchestrator, Piper outreach, Rex the scout, Penny the
modeler, Wen the lawyer, and so on). When you ask something real, the **9-phase dispatch**
fires automatically: classify the task, send 3-plus agents in parallel, have them
cross-check each other, then one agent merges it into a single answer. That is how a guy
with no staff runs a "team." This very gameplan was built by **9 agents across two passes** --
you didn't do the laundromat research, the car-wash competitive teardown, the tax-domicile
analysis, or the funnel math. They did. You read the conclusions.

### 3. e5-mother = the always-on brain (the server)
An Oracle ARM cloud box, on 24/7. It holds:
- **Blinko** -- the searchable memory of every session (your "remember everything" layer).
- **MCP tools** -- the wired, logged connections to Gmail, Slack, Supabase, the broker
  pipeline, market data. This is the auth + audit boundary for everything that touches
  the outside world.
- **Open WebUI + voice** -- chat surfaces.
This is what runs when your phone is off. It is the org's memory and its always-on compute.
*Honest status today: reachable over the private tailnet, but UNREACHABLE from the phone
right now -- which is why this session's logs are queued locally instead of live in Blinko.*

### 4. Oracle Micro = the money machine that never sleeps
A separate cloud box that runs **only** the XLM trading bot + its price feed, 24/7. Nothing
else is allowed to touch it (it's sacred -- one job). *Honest status: the bot is net negative
over its last 100 trades, so it is "running" but not yet "earning." It's R&D until it proves
itself, per the gameplan.*

### 5. The automation layer = the part that works while you sleep
`03_AUTOMATION_CORE/01_Scripts/` + cron jobs. This is the engine room:
- **Wholesale pipeline** -- distress finder, probate scout, tax-delinquency scan, Zillow
  keyword scrapers. They hunt leads on a schedule. **This is the Phase-0 engine that funds
  Deal 1, the $17k, and your house-hack.**
- **Branded comms** -- every email/Slack/doc/report ships through the gold-template pipeline
  so a prospect sees a premium business, not a one-man operation.
- **deploy_to_oracle.sh** -- pushes phone edits to the live servers automatically.
- **Health monitors + drift audits** -- keep the machine honest while you're not looking.

### 6. everlightventures.io = the storefront
A React site on Cloudflare Pages that reads from Supabase. It's the public face -- where
the **Open Deal buyer page** lives. When a seller or cash buyer lands here, they see a
"premium premier business entity," not where you slept last night. That gap is the point:
the machine lets the operation look bigger than its current circumstances, which is exactly
how you close the deal that changes the circumstances.

### 7. Supabase = the vault
The single source of truth for all production data -- the deal pipeline, leads, matches,
payments. Dashboards and the site read from here. Nothing important lives only on the phone.

### 8. The device mesh
Phone (cockpit) <-> e5-mother (brain) <-> Oracle Micro (bot) <-> AceMagician PC (heavy
compute, peer cache) <-> ev-box (planned ops box). They're linked over a private tailnet.
The rule is **offline-first**: when one node can't reach another, writes queue and reconcile
on reconnect -- so couch-hopping with spotty wifi never loses your work. (You're watching
that rule work right now: Blinko's down, so the logs are queued, not lost.)

### 9. The repos / "745 repos" catalog
The open-source stack (`06_DEVELOPMENT/everlight_os/hive_mind/open_source_repo_stack.yaml`)
is the parts bin -- curated tools the Hive pulls from to build fast instead of from scratch.
The binding rule: build ON TOP, never break what's running (e.g., the XLM bot's core is
left untouched).

---

## How it all connects to the gameplan (the chain)

```
  Wholesale crons + Hive scouts find leads
        |
        v
  Branded mailer + Open Deal page (on the site)  ->  seller/buyer engages
        |
        v
  Broker OS pipeline (Supabase) tracks the deal  ->  Deal 1 closes (~$3.5k)
        |
        v
  5 deals = $17k  ->  Airbnb arbitrage  ->  house-hack (FHA + CalHFA)  ->  YOU'RE HOUSED
        |
        v
  Wealth_OS tiers turn on (T0 -> T1 -> T2 ...) as net worth climbs
        |
        v
  laundromat / self-serve car wash / self-storage  ->  refi-recycle  ->  the ladder
```

- **The memory layer (Blinko + memory files + AGENT_MAILBOX)** = how the plan survives you
  moving between couches and devices. It's your continuity. It's also our substitute for
  cross-chat recall: I can't read old chats verbatim, but I read these every session.
- **The Wealth_OS engines** (Quarterly Intel, Audit Defense) = automation that tracks
  tax-law changes and keeps your R&D / mileage / water-bill files audit-ready as you climb.

---

## Bring it all the way back to Earth

- You shower at Planet Fitness. That is not a hole in the plan -- it's **field research**.
  The PF -> laundromat -> storage -> Airbnb ecosystem you described is the life you're
  living. You are planning to build the exact businesses you personally need. That instinct
  is real and it's good.
- The entire machine, today, has one purpose: **get you off the couch and into a
  house-hacked door.** Cannabis, caviar, the family office, the community -- all later. The
  near-term mission is housing + stability, funded by wholesale.
- You don't need to feel disorganized about it anymore. As of today every living folder has
  a README that says what it is. The gameplan has a single spine file. The machine has this
  doc. When you feel lost, you open three files: the spine, this doc, and the folder's README.

---

## Honest gaps (so this is real, not a brochure)

- **Built and working:** the workspace + memory + Hive dispatch + branded pipeline +
  wholesale lead crons + Broker OS MVP + the site + e5-mother base (Blinko) + the XLM bot.
- **Built but not yet paying off:** XLM bot (R&D, net negative); Open Deal page (pending
  legal countersign + LLC); e5-mother MCP fleet (partial -- some servers not migrated).
- **Not done / deferred:** Deal 1 not closed (the gate to everything); Django ops dashboard
  deferred; NV entity not formed (waiting on Deal 1 fee); phone-to-cloud memory sync partial.
- **Right now:** Blinko unreachable from the phone (logs queued); WORKSPACE_MANIFEST was
  stale (refreshed); the tree was 2/10 navigable (READMEs now scaffolded across 130 folders).

The machine is real and most of it runs. What it has not yet done is close the first deal.
That's the only number that matters next. Everything in this document exists to make that
one event happen, and then to catch the money when it does.
