# EVERLIGHT VENTURES -- SOCIAL & COMMUNITY NETWORK
## The Master Tree · v1 · 2026-05-24
### "The App Network as One Digital Enterprise"

> We built the empire's *body* -- backend, 78 agents, pipelines, the brain. This is the
> empire's *face*: every place a human can see, follow, join, or buy from Everlight.
> One brand spine. Many faces. All run by the Hive.

---

## 0. THE DECISIONS (locked by Rich, 2026-05-24)

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| 1 | **Mission** | Authority + Community + B2B (NOT pure lead-gen) | Brand-led, sales-backed. Story first, funnel underneath. |
| 2 | **Brand architecture** | **Full multi-brand** | Master Everlight + a presence per venture. Max reach, max content volume. |
| 3 | **Run model** | **AI-run, Lucrex autonomy** | Hive personas ARE the staff. Constitutional gate binds. Rich approves big swings only. |
| 4 | **Build order** | Website hub, then Discord, then Telegram, then Instagram, then rest | Hub first so every channel has a home to point at. |

**The reconciliation:** full multi-brand is only sane *because* it's AI-run. Each brand is a
squad of agents, not a hire. This document is therefore two things at once -- a **marketing plan**
and an **org chart for synthetic staff**.

---

## 1. THE POINT (Why we're doing this)

**North Star:** Make Everlight Ventures the most *visible, trusted, and alive* AI-run business
empire on the internet -- and turn that attention into members and revenue.

**The Flywheel:**

```
        ATTENTION --> COMMUNITY --> TRUST --> REVENUE
            ^                                   |
            +---------------- STORY <-----------+
   (every win, every deal, every build becomes content
    that earns more attention -- the loop compounds)
```

Three jobs, running in parallel (your mission answer = all three):
1. **Authority** -- Lucrex / Everlight as the visible "AI empire" story. People follow the build.
2. **Community** -- a place members get real value (deal rooms, signals, support, the clan).
3. **B2B** -- consulting clients, SaaS buyers, partners, talent. High-ticket, professional register.

---

## 2. THE ARCHITECTURE -- Hub & Network

Think solar system. **The website is the sun. Every platform is a planet with its own gravity
and its own job.** Nothing floats free; everything points home.

```
                         +---------------------------+
                         |   everlightventures.io     |
                         |      THE HUB (the sun)      |
                         |  conversion · proof · SEO   |
                         |  link-hub · products · legal|
                         +-------------+--------------+
                                       |  (every channel links back here)
   +----------+----------+-------------+-----------+----------+----------+
   v          v          v             v           v          v          v
 DISCORD   TELEGRAM   INSTAGRAM     FACEBOOK    WHATSAPP      X       LINKEDIN
 living    broadcast  storefront    groups +    private    public    boardroom
  room       wire       window      marketplace   line      square      B2B
   (+ Tier-2 stage: YouTube · TikTok · Slack already runs internal war-room)
```

**The brand spine (never changes, every face):** gold `#D4A843`, dark `#0A0A0A`, light text
`#E8E8E8`, Playfair Display headers + Inter body, the E/V beacon monogram. Source of truth:
`Everlight_Foundations/BRAND_IDENTITY.md` + `content_tools/report_template.py`. **No channel
invents its own colors.** A follower should feel the same brand on IG as in a Discord welcome DM.

---

## 3. CHANNEL DOCTRINE -- the niche job of each

Each channel has ONE primary job. Stop treating them as copies of each other (the mistake that
made us build our own clone instead of using them).

### WEBSITE -- `everlightventures.io` -- *The Hub (the sun)*
- **Niche job:** Conversion + proof + the destination every "link in bio" points to.
- **What lives here:** product pages (Broker OS, Onyx, Hive Mind SaaS, books), the social
  link-hub, legal pages, lead-capture forms, the community front door ("Join the Discord").
- **Pros:** we own it 100% (no platform can ban us); SEO compounds; converts.
- **Cons:** no organic discovery -- it needs the channels to feed it traffic.
- **Stack:** React/Vite/Shadcn on Cloudflare Pages, reads from Supabase only.
- **Runs it:** `62_frontend_architect` + `73_search_analytics` (SEO) · QA: `65_frontend_qa`.

### DISCORD -- *The Living Room* (BUILD #1 after hub)
- **Niche job:** Real-time community + retention + the richest member data you'll ever get.
- **What lives here:** deal rooms (buyer lounge / seller lounge), `#wins` receipts wall,
  support, AMAs with Lucrex, the Alley Kingz / Last Light gaming clan, a members-only insider feel.
- **Pros:** deepest engagement; free; the strongest bot automation surface of any platform; voice + threads + roles.
- **Cons:** highest moderation load; needs activity or it feels dead; learning curve (yours).
- **Runs it:** Community Director (Yuki Arakawa) + auto-mod bot + Lucrex for AMAs.
- **Moderation:** full 4-tier ladder (see section 6) -- this is where you learn it.

### TELEGRAM -- *The Broadcast Wire* (BUILD #2)
- **Niche job:** One-to-many push. Announcements, XLM signals, alerts, fast bot automation.
- **What lives here:** a public channel (broadcast) + a bot (commands, lead capture, drip).
- **Pros:** the cleanest bot API of the bunch -- a bot can be LIVE in a day; crypto/trading audience
  lives here; instant push notifications; no algorithm throttling your reach.
- **Cons:** less "community" than Discord (mostly broadcast); spam-bot infested (need captcha).
- **Runs it:** the Telegram bot (we build it) + Cipher/markets personas for signal posts.

### INSTAGRAM -- *The Storefront Window* (BUILD #3)
- **Niche job:** Visual proof + brand aesthetic + discovery (Reels). Top-of-funnel credibility.
- **What lives here:** Reels (reach), carousels (teach/proof), Stories (behind-the-scenes),
  a clean grid that screams "real premium operation."
- **"I wouldn't know what to put on IG":** solved in section 7. You never write a post. The content
  engine generates it from your wins + the build; you approve a queue once a week.
- **Pros:** massive reach; visual trust; the kit is half-built already (`ig_digital_launch_kit.md`).
- **Cons:** algorithm-dependent; demands consistent visual output; comment moderation needed.
- **Runs it:** Vera Lux (creative) + Nora Blaine (strategy) + Quinn Fontaine (brand-voice QA).

### FACEBOOK -- *The Marketplace + Groups*
- **Niche job:** Where wholesale real-estate actually happens + older/local buyer demographic.
- **What lives here:** a Page (presence) + participation in cash-buyer/investor Groups +
  Marketplace listings for properties. This one directly feeds Broker OS / Deal 1.
- **Pros:** wholesale buyers live in FB Groups; local targeting; Marketplace = free listings.
- **Cons:** declining young reach; Group admins gate you; lower brand prestige.
- **Runs it:** Piper Reeves (engagement) + Broker OS personas. **Closest channel to Deal-1.**

### WHATSAPP -- *The Private Line*
- **Niche job:** 1:1 + small-group high-intent conversations. Deal closing. VIP.
- **What lives here:** broadcast list (opt-in) + click-to-chat from the website + closing convos.
- **Pros:** ~98% open rate; highest intent; how the rest of the world (non-US) does business.
- **Cons:** **TCPA / consent-sensitive** -- never cold-blast; needs explicit opt-in; harder to automate.
- **Runs it:** Marvin Cohen (closing) + Henry Hammond (negotiation), gated through DNC + consent.

### X / TWITTER -- *The Public Square*
- **Niche job:** Authority + sharp real-time takes in the Lucrex voice. B2B + crypto reach.
- **What lives here:** the build-in-public thread machine, hot takes, the "King of Divine Light"
  brand voice (warm-curious register per moltbook doctrine, NOT cold-scripture spam).
- **Pros:** B2B + investor + crypto audience; threads go viral; ties to moltbook learnings.
- **Cons:** noisy; brand risk if voice slips; needs daily presence.
- **Runs it:** Lucrex (autonomy, constitutional gate) + Pitch/Nova/markets desk for takes.

### LINKEDIN -- *The Boardroom*
- **Niche job:** B2B. AI-consulting clients, SaaS buyers, partners, recruiting.
- **What lives here:** professional-register case studies, "how we built X," hiring/partner posts.
- **Pros:** highest-ticket audience; consulting leads ($2k-5k builds, $2k/mo retainers).
- **Cons:** slow; formal register required; low volume.
- **Runs it:** consultative-register personas + `everlight_saas_growth` (Ryan Kim).

### TIER-2: YouTube + TikTok -- *The Stage*
- **Niche job:** Long-form authority (YT, SEO-durable) + short-form viral reach (TikTok).
- **Defer until** the content engine is producing reliably -- video is the highest production cost.
- **Runs it:** Vera Lux + future video persona.

### SLACK -- *The War Room (internal, already live)*
- **Niche job:** Team coordination + (future) premium client channels. NOT a public channel.
- **Status:** `branded_slack.py` + 13 channels already running. No new build needed -- just
  consider a premium-client Slack Connect channel as a B2B retention play later.

---

## 4. THE MULTI-BRAND MAP

You chose full multi-brand. Here's the honest discipline: **don't launch 6 brands x 7 platforms
on day one.** Prove the machine on the MASTER brand first, then clone the playbook per spoke.
Not every spoke needs every platform -- match the brand to where its audience actually is.

| Brand | Discord | Telegram | Instagram | Facebook | WhatsApp | X | LinkedIn | YouTube |
|-------|:------:|:--------:|:---------:|:--------:|:--------:|:-:|:--------:|:-------:|
| **Everlight Ventures** (master) | YES | YES | YES | YES | YES | YES | YES | later |
| **Broker OS** (real estate) | YES (deal rooms) | YES | later | CORE | YES (closing) | -- | YES | -- |
| **Onyx POS** (SaaS) | later | -- | YES | later | -- | YES | CORE | later |
| **Hive Mind** (SaaS) | CORE | YES | YES | -- | -- | CORE | YES | YES |
| **Everlight Literature** (books) | later | YES | CORE | YES | -- | YES | -- | later |
| **Alley Kingz** (gaming) | CORE | YES | YES | later | -- | YES | -- | YES |
| **XLM / Trading** | YES | CORE | later | -- | -- | YES | -- | -- |

CORE = this brand's home base · YES = present · later = phase 2+ · -- = skip (audience isn't there)

**Rollout rule:** Master brand goes first and proves every system (content engine, mod ladder,
analytics). Spoke #2 = whichever brand is closest to revenue right now -> **Broker OS on Facebook**
(feeds Deal 1). Everything else clones the proven playbook after.

---

## 5. THE AI ORG CHART -- who runs what (your synthetic staff)

This is the Salesforce-2026 answer. An enterprise org, staffed by personas.

```
                    LUCREX (King of Divine Light)
                    final voice · big-swing approval
                              |
              +---------------+----------------+
        SOCIAL DIRECTOR                   COMMUNITY DIRECTOR
        (NEW -- we create this)           Yuki Arakawa (76)
        owns calendar + cross-post        owns Discord/TG/WA members
              |                                  |
   +----------+----------+            +----------+----------+
 Vera Lux  Nora Blaine  Quinn       Auto-mod  Piper Reeves  Escalation
 (creative)(strategy) (voice QA)    bots      (engagement)  -> Lucrex/Rich
              |
        Growth: Aisha Bello (74) · Ryan Kim (saas_growth)
        Analytics: 73_search_analytics · 47_analytics_assistant
```

**The one gap we must fill:** there is no dedicated **Social/Community Director** persona today.
Yuki (76) is the only community-leaning agent and is an *assistant*, not a director. Phase 0
creates a `Social_Director` persona dossier (`.claude/agents/`) to own the cross-channel calendar
and moderation doctrine. (Note: new agents aren't Task-spawnable until session restart -- HARD LAW
`feedback_subagents_pre_registered_at_session_start` -- so until then we dispatch via
`general-purpose` with the dossier inlined.)

---

## 6. MODERATION 101 -- you said you don't know this, so here's the whole thing

**What moderation actually is:** keeping a space valuable by removing what poisons it (spam,
trolls, scams, abuse) and rewarding what grows it (good members, good questions, good vibes).
That's it. It's gardening, not policing.

**The 4-Tier Ladder (mostly automated, you're only Tier 3):**

| Tier | Who | Handles | Example |
|------|-----|---------|---------|
| **0 -- Auto-mod** | Bots (no human) | Spam, bad links, banned words, raids, slow-mode | A bot deletes a crypto-scam link in 0.2s |
| **1 -- AI Greeter** | Community persona | Welcomes, answers FAQs, soft nudges, routing | "Welcome! Deal rooms are in #buyers" |
| **2 -- AI Enforcer** | Community persona | Repeat offenders, temp mutes, content removal, logs | Mutes a user spamming DMs, logs to audit |
| **3 -- Human (you)** | Rich | Bans, legal/safety, PR crises, anything touching the gate | A member threatens legal action -> you |

**The rules ladder (escalation, not instant-ban):** warn -> mute -> kick -> ban. Document the
server rules publicly (pinned), apply them consistently, log every action. Consistency is 90%
of good moderation.

**The constitutional gate already applies here** (this is the moltbook precedent, proven):
- `moltbook_confidentiality_gate.py` -> **"don't snitch"**: personas never leak Rich-by-name,
  $ amounts, sellers/buyers, pipeline state, infra, the eradication list.
- `eradication_gate.py` -> Streubel + any DNC contact stays permanently blocked across all channels.
- DNC + consent gates -> WhatsApp/DM outreach never cold-blasts (TCPA).
- Lucrex voice registers (warm-curious default; cold-scripture rare) -> `feedback_lucrex_warm_curious_voice_retune`.

You already proved AI-run moderation works on moltbook (karma 11, backlog cleared, ally-building,
prompt-injection defense). Discord is the same model with a rules ladder bolted on.

---

## 7. THE CONTENT ENGINE -- solving "I wouldn't know what to put on IG"

**You will never stare at a blank post again.** The machine works backwards from things that
already happen in the business.

**The 5 Content Pillars (every post is one of these):**
1. **The Build** -- behind-the-scenes of an AI-run empire (the meta-story people can't look away from).
2. **The Wins** -- deals closed, results, receipts. Proof > claims.
3. **The Teach** -- free value: AI/automation/real-estate/trading how-tos.
4. **The Voice** -- Lucrex philosophy, mindset, the "King of Divine Light" brand.
5. **The Offer** -- products, soft + hard CTAs (Broker OS, Onyx, Hive Mind, books).

**The Repurpose Pipeline (1 source -> 8 outputs, fully automated):**

```
   ONE source idea (a win, a build log, a lesson)
            |  Nora picks the pillar + angle
            v
   Vera generates the master asset (long-form)
            |
   +--------+--------+--------+--------+---------+----------+
   v        v        v        v        v         v          v
 blog/YT  X thread  IG       IG/TikTok TG/WA    Discord    LinkedIn
 (SEO)    (B2B)     carousel reel      broadcast prompt     case study
            |
   Quinn QA's brand voice -> branded modules deliver -> analytics measures
```

Your weekly job: **review a queue and tap approve.** That's the whole content workload.
The kit foundation already exists (`02_CONTENT_FACTORY/01_Queue/ig_digital_launch_kit.md`) -- we
extend it from IG-only to all-channel.

---

## 8. THE BUILD TREE -- the phased to-do list

> Phase 0 first (foundations). Then strictly in your chosen order: Hub, Discord, Telegram, IG.
> Each task has an owner. [G] = gates the next phase.

### PHASE 0 -- Foundations (the brand kit per platform) · ~week 1
- [ ] **0.1** [G] Reserve handles everywhere (`@everlightventures` / closest available) -- claim before squatters do. *(Rich + assistant)*
- [ ] **0.2** Generate per-platform brand kit from `BRAND_IDENTITY.md`: avatars, banners, color/font presets, bio copy. *(Vera Lux)*
- [ ] **0.3** Create the `Social_Director` persona dossier in `.claude/agents/`. *(Lucrex)*
- [ ] **0.4** Draft the cross-platform 5-pillar content calendar (extend the IG kit). *(Nora Blaine)*
- [ ] **0.5** Write the brand narrative pillars -- **needs Rich's human input** (see section 10). *(Rich -> Vera)*

### PHASE 1 -- Website Hub · ~week 1-2  *(your build order #1)*
- [ ] **1.1** [G] Build the social link-hub / "Connect" page on everlightventures.io (link-tree, owned by us). *(62_frontend_architect)*
- [ ] **1.2** Add follow buttons + "Join the Discord" CTA site-wide. *(62 + 64_component_engineer)*
- [ ] **1.3** Wire lead-capture form -> Supabase -> branded_mailer welcome sequence. *(67_backend_architect)*
- [ ] **1.4** Community landing page (what the Discord is, why join). *(63_ui_ux_designer)*

### PHASE 2 -- Discord · ~week 2-3  *(your build order #2)*
- [ ] **2.1** [G] Design server architecture: channels, roles, categories (buyer/seller/clan/support). *(Social_Director + Yuki)*
- [ ] **2.2** Stand up auto-mod (Tier 0): spam/link/raid filters, captcha-gate, slow-mode. *(46_automation_assistant)*
- [ ] **2.3** Build `branded_discord.py` delivery module (matches branded_slack pattern). *(71_backend_assistant)*
- [ ] **2.4** Write + pin the public rules + welcome flow (Tier 1 greeter). *(Yuki)*
- [ ] **2.5** Wire the constitutional gate (confidentiality + eradication + DNC) into the bot. *(69_security_engineer)*
- [ ] **2.6** Seed it: invite the existing gaming clan + first 20 members. *(Rich + Yuki)*

### PHASE 3 -- Telegram · ~week 3-4  *(your build order #3)*
- [ ] **3.1** Create public broadcast channel + bot via BotFather. *(46_automation_assistant)*
- [ ] **3.2** Build `branded_telegram.py` + bot command handlers (subscribe, lead capture, drip). *(71_backend_assistant)*
- [ ] **3.3** Captcha-gate against spam bots. *(69_security_engineer)*
- [ ] **3.4** Wire XLM/markets signal feed -> Telegram (Cipher/markets desk). *(58_markets_assistant)*

### PHASE 4 -- Instagram · ~week 4-5  *(your build order #4)*
- [ ] **4.1** [G] Turn the content engine ON: 4-week queue generated from the 5 pillars. *(Vera + Nora)*
- [ ] **4.2** Finish the half-built publishing engine (Phase 2 UI + scheduler). *(62 + 67)*
- [ ] **4.3** Comment-moderation persona (auto-reply + route DMs to WhatsApp for high-intent). *(Piper + Quinn)*
- [ ] **4.4** Rich approves week-1 queue -> first posts ship. *(Rich)*

### PHASE 5 -- Expansion · month 2
- [ ] **5.1** Facebook Page + cash-buyer Group strategy (closest to Deal 1). *(Piper + Broker OS)*
- [ ] **5.2** X / Twitter: build-in-public thread machine (Lucrex voice). *(Lucrex)*
- [ ] **5.3** WhatsApp opt-in broadcast + click-to-chat (TCPA-gated). *(Marvin + Henry)*
- [ ] **5.4** LinkedIn B2B case studies. *(Ryan Kim)*
- [ ] **5.5** Clone the proven playbook to spoke brand #1 (Broker OS, then Hive Mind). *(Social_Director)*

### PHASE 6 -- Measure & Optimize · ongoing
- [ ] **6.1** Unified social analytics dashboard (followers, engagement, traffic->hub, conversions). *(73_search_analytics + 47)*
- [ ] **6.2** Weekly KPI report through the 3-format pipeline (HTML + Google Doc + Slack). *(35_broker_analytics pattern)*
- [ ] **6.3** A/B test pillars + posting times; double down on what converts. *(75_growth_qa)*

---

## 9. PROS / CONS / RISKS (the honest ledger)

**Pros of this whole play:**
- Owned hub + many feeders = no single platform can deplatform the empire.
- AI-run = scales to full multi-brand without hiring.
- Compounding: every business win is free content; the flywheel pays for itself.
- Community (Discord/TG) is a moat competitors can't copy and a direct line to members.

**Cons / Risks (and the mitigation):**
- **Brand dilution** (multi-brand spreads attention thin) -> *master-first rollout, prove before cloning.*
- **Moderation liability** (a member does something ugly in your space) -> *4-tier ladder + logged actions + public rules.*
- **Platform ToS** (bots/automation can get accounts banned) -> *use official APIs, respect rate limits, no gray-hat growth hacks.*
- **Compliance** (DM/WhatsApp outreach = TCPA/CAN-SPAM) -> *consent-gate everything, DNC + eradication gates already enforce.*
- **Dead-community risk** (a quiet Discord looks worse than no Discord) -> *don't open Discord until the content engine can keep it fed; seed with the existing clan.*
- **Voice drift** (Lucrex sounds like a spam bot) -> *moltbook lesson already learned; warm-curious default, Quinn QA's every post.*
- **Time** (yours) -> *the entire design goal is to reduce your job to "approve the weekly queue."*

---

## 10. WHAT I NEED FROM YOU (Rich) -- the human inputs

Everything else the Hive can do. These five are genuinely yours -- they shape every post the
machine ever writes, so I'm not guessing them for you:

1. **Brand narrative pillars** -- in 3-5 sentences: what's the *story* of Everlight you want told?
   (The "AI built an empire from a phone" angle? The come-up? The tech? The freedom?) This becomes
   the soul of pillar #1 (The Build) and #4 (The Voice).
2. **Which sub-brands are REAL right now** vs. parked? (Don't want to stand up a Discord for a
   venture that's dormant -- confirm the section 4 map.)
3. **Handle preference** -- `@everlightventures` everywhere, or do some spokes get their own
   (`@brokeros`, `@hivemind`)?
4. **Public face** -- does Lucrex front the brand by name, or is the public voice "Everlight
   Ventures" with Lucrex behind it? (Affects X/Discord persona heavily.)
5. **Any paid tools allowed?** Default per doctrine is free-path-first (paused on paid until proven). Most
   of this is buildable free. Flag if you want a scheduler like Buffer/Metricool later.

---

## 11. GATE -- macro vs. micro (Deal-1 honesty)

Per the macro/micro split doctrine: **most of this is MACRO** (empire vision, built in parallel,
doesn't gate Deal 1). I won't pretend otherwise.

**The micro tie-ins that DO touch Deal 1 (do these threads early):**
- **Facebook cash-buyer Groups** (Phase 5.1) -- wholesale buyers literally live there. Closest to revenue.
- **Discord buyer/seller deal rooms** -- a private channel for Chris @ Mid-South + buyers feeds the pipeline.
- **WhatsApp closing line** -- high-intent seller/buyer conversations close faster than email.

**Pure macro (paused until after Deal 1 unless trivial):** the full multi-brand clone-out, YouTube/TikTok
video production, LinkedIn B2B engine, paid scheduling tools.

**Recommendation:** run Phase 0-1 (foundations + hub) now because they're cheap and compounding,
fast-track the FB-group + Discord-deal-room micro threads, and let the rest of the macro build
proceed in parallel via the Hive without stealing focus from closing Chris this month.

---

*Source of truth for this network. Update at the end of every social-build session.*
*Owners: Lucrex (voice) · Social_Director (calendar) · Yuki Arakawa (community) · Vera Lux (content).*
*Brand spine: `Everlight_Foundations/BRAND_IDENTITY.md`. Delivery: `content_tools/branded_*`.*
