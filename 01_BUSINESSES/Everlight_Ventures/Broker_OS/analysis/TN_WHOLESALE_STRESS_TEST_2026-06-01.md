<!--
STRESS-TEST RUN METADATA
  Run ID:        wf_3f5a9d13-e0c  (workflow: tn-wholesale-stress-test)
  Date:          2026-06-01
  Method:        5 adversarial angles -> per-finding independent verification (steelman-the-defense) -> single synthesis
  Agents:        32 total | 2.16M tokens | 399 tool uses | ~27 min
  Findings:      26 high-severity verified -> 16 confirmed -> 1 FATAL
  Angles:        Market (Cipher) | Financial (Penny) | Legal (Theo+Justine) | Execution (Marcus) | Moat (Solomon Vale)
  Note:          Agents read live code/data files, not just the brief, so they surfaced the FATAL entity bug + funnel_model.py
                 math error + missing stripe_invoicer.py that the brief did not contain.
-->

# TENNESSEE WHOLESALE / BROKER OS -- STRESS-TEST VERDICT
**Marcus Cole, Chief of Staff to Lucrex | For Operator Eyes (Rich) | 2026-06-01**

---

## 1. VERDICT

**CONDITIONAL GO -- confidence HIGH (on the diagnosis), confidence LOW (on the current execution path).**

Keep the engine, but it is **not a business yet -- it is a pre-revenue R&D lab with a real legal blocker on its load-bearing instrument.** After 81 days, 3,467 leads, and 84 buyers, the system has sent **0 emails in the last 30 days**, produced **0 responses ever**, closed **0 deals**, and collected **$0** -- the only invoices on file are 4 self-billed test invoices to your own Gmail. None of that kills the model; per-deal economics ($5.7k to $36.9k on Memphis appraisals) are real and one warm close covers the entire annual cost stack many times over. But there is **one FATAL finding the others all missed**, and it must be cleared before a single TN contract is signed: every contract template names a different, non-existent legal entity, which voids your SB 909 disclosure and strips your liability veil on Deal 1. Fix the entity, wire the compliance gate, ship one real send, then it's a GO.

---

## 2. THE KILL LIST
*Confirmed serious/fatal only. Ranked by what sinks the boat fastest.*

**#1 -- FATAL: The contract stack names 5 conflicting legal entities, none in good standing.**
- **Risk:** Your live contracts bind "Everlight Logistics LLC" (finder template), "Everlight Ventures Wholesale Acquisitions, LLC" (sender config), "Everlight Ventures, LLC d/b/a Everlight Logistics" (assignment contract), and even **"Marquise Smith"** -- a verified template-corruption bug -- on the PSA base that carries the SB 909 disclosure. Your actual posture is sole prop (Richard Gee personally liable, no veil).
- **Assumption it breaks:** That "operating as sole prop until LLC reinstated" is a clean posture and SB 909 disclosure is satisfiable as papered.
- **Consequence:** The first TN deal you sign is simultaneously (a) a misrepresentation-of-party defect, (b) a defective SB 909 disclosure exposing you to **$10k statutory damages + attorneys' fees**, and (c) a personal-liability event with no corporate veil. Three independent rescission/fraud hooks on one signature, handed to a counterparty pool that **already produced one litigating attorney (Streubel).** `contract_generator.py` emits two contradictory principals at runtime (L41 finder = "Everlight Logistics LLC"; L420 PSA = "Richard Gee d/b/a Everlight Ventures"). This is the only fatal finding in the entire dossier and it sinks Deal 1 itself.

**#2 -- SERIOUS: The revenue target is mathematically impossible at the rig's capacity, and the headline math has a 5x units error.**
- **Risk:** Doctrine says "5 deals/mo at ~$5k = $5k/mo base." That's wrong twice. 5 x $5k = $25k, not $5k. And the team's *own* `funnel_model.py` proves 5 deals/mo needs **168 emails/day + 1,398 addresses/day**; the rig caps at 25 to 30 emails/day and 25 parcels/day. Even the best-case preset needs 50/day. Forward projection at the cap = **~1.6 deals/mo**, and actuals are **0**.
- **Assumption it breaks:** That the $5k/mo base is reachable on the current pipeline in anything like month 1.
- **Consequence:** Every projection downstream inherits a 5x deal-count error stacked on an unfunded throughput assumption. The *dollar* goal survives (one ~$5k deal/mo needs only ~10 emails/day, inside the cap), but the published plan is fiction until restated.

**#3 -- SERIOUS: Seller-side contact is throttled to single digits -- ~9 to 11% email capture and the skip-trace unlock is gated behind the deal it must produce.**
- **Risk:** Of 2,510 TN leads, 286 have *any* email (11.4%) and **zero are verified** -- all 283 scored are "try"-tier OSINT guesses (`marco.wlliams@gmail.com` with the owner-name typo baked in), max confidence 39/100. Real reachable inventory is ~9. Phone-side skip-trace is Cloudflare-blocked; the $30/mo BatchSkipTracing fix is deferred "post-Deal-1."
- **Assumption it breaks:** That 3,467 leads = deep, reachable seller supply.
- **Consequence:** Classic chicken-and-egg -- the volume unlock is locked behind the volume it produces. Until broken, "thousands of leads" is a vanity metric; the real warm TN pipeline is ~34 owner-named parcels, 0 with verified email.

**#4 -- SERIOUS: Demand is one verified buyer deep, and even that one isn't actually verified in the canonical DB.**
- **Risk:** The entire TN engine gates open on "Chris @ Mid South Homebuyers, verified 2026-04-27." But the operational `buyers_db.json` shows that record as **status=contacted, responded=false, deals_closed=0** -- a single unanswered cold email. The "verified" relationship is a quoted courtesy line ("no limit to the deals we'll take"), not a contract. All 84 buyers show 0 responses, 0 deals. The other 8 TN buyers are cold contacts. The 75 non-TN buyers are legally unreachable under the TN-only lockdown.
- **Assumption it breaks:** That 84 buyers = durable demand depth.
- **Consequence:** Single point of failure on the demand side. If Chris's buy-box doesn't fit or he passes, Deal 1 has no proven home and you have zero fee-negotiation leverage. And because leads come from a public Shelby County tax CSV, Chris (a dominant Memphis acquirer) can pull the same source and bypass you -- zero switching cost.

**#5 -- SERIOUS: The closed-to-paid pipeline is broken and forked -- it has never recorded a dollar and would fail silently the first time real money moved.**
- **Risk:** `deal_tracker.json` is empty (active/closed/dead/ledger all []). `stripe_invoicer.py` **does not exist**, so the invoice call in `rex_closer.py` is permanently dead code. `close_deal()` has **zero callers** and writes to a different store than the dashboard's commission ledger reads, so even a successful close populates nothing.
- **Assumption it breaks:** That the system can capture and collect a fee once a deal happens.
- **Consequence:** The first real deal discovers the collection rails are broken *live*, at the worst possible moment, with the $50k bond wall arriving at deal 3.

**#6 -- SERIOUS: The Streubel failure surface re-arms the instant you unblock sends.**
- **Risk:** The recipient-classifier (gov/attorney/homeowner block) **is built and correct in isolation but is NOT wired into the send chokepoint** (`branded_mailer.py` / `safe_send_email`). The eradication gate protects exactly one human (Streubel by name). Two live-wired raw senders (`rex_autonomous.py:399`, `rex_daily_run.py:360`) still POST to api.resend.com with a `SMTP_FROM` env that can be set to *any* alias, bypassing the entire compliance stack -- the exact Streubel root cause.
- **Assumption it breaks:** That it's safe to resume outreach once the CAN-SPAM config is set.
- **Consequence:** The system can only ever catch the *second* Streubel, never the first. The 3.4% historical misfire rate (3 .gov + 1 attorney sends) recurs on first contact, on top of an existing C&D + BBB complaint, with SB 909-class statutory exposure.

---

## 3. CROSS-ANGLE COMPOUNDING
*The 3 root causes that explain ~80% of every finding above.*

**ROOT CAUSE A -- "The clock has never started." One $0-cost config gate (CAN-SPAM sender_identity = PENDING) sits in front of everything, behind a second empty pipe (no verified emails).**
This single fact is *why revenue is $0* (Penny, Marcus), *why conversion looks like 0%* (Cipher), *why the "77 engaged" leads are vanity* (Cipher, Penny -- they're newsletters and casino receipts, never contacted), and *why the funnel can't be evaluated at all*. Every angle independently arrived here. The compounding insight the verifiers added: **fixing the CAN-SPAM config alone unblocks nothing** -- all 42 TN tracker leads are `email_needed` with 0 emails, so `send_plan()` returns 0 regardless. You must fix **both** gates, in order: skip-trace to get verified emails *then* the deliverable address. This is the cheapest, highest-leverage fix in the whole plan and it is the literal start button.

**ROOT CAUSE B -- "Activity instrumented as success." The whole system measures invocations, not outcomes, which is how a dead engine went unnoticed for a month while reporting green.**
This is the deepest finding and it connects Marcus's agent-theater finding (Piper 14/14 success / 0 emails; Calvin 12/12 / 0 matches; Carlos 9/9 / 0 commissions), Cipher's "77 engaged is an IMAP artifact," and Penny's "2,469 matched but only 8 leads score >=70" (a 300x decoupling between the claimed gate and the real one). **The same defect -- counters that increment on activity, not output -- is why the autonomous machine could not detect or repair its own dead state for 30+ days.** That is the Samantha-Law failure pattern repeating. Until "success" means *produced artifact* and a 0-send watchdog fires within hours, more time and more leads reproduce the same $0.

**ROOT CAUSE C -- "The map names a company that doesn't exist." A single missing canonical-entity constant cascades into the one FATAL finding AND the compliance exposure AND the contract-theory confusion.**
The 5-entity mess (#1), the finder-vs-assignment contract contradiction, and the Streubel re-arm surface (#6) all trace to the same discipline gap: **no single source of truth propagated to the chokepoints.** Legal needs ONE entity constant; compliance needs ONE send chokepoint; the closer needs ONE contract per deal type. The fix is architecturally identical in all three -- collapse to one canonical value, enforce at one gate, fail closed. This is also why the verifiers *downgraded* several "fatal" claims to manageable: the protective logic mostly *exists*, it's just not wired to the single point where it would bind.

---

## 4. THE FIX LIST -- SEQUENCED PATH TO DEAL 1
*Free-first respected. DONE-vs-PLANNED honest: everything below is PLANNED -- nothing here is done yet.*

**GATE 0 -- LEGAL BLOCKER (must be FIRST, $0 to $800, blocks Deal 1 itself):**
1. **PLANNED:** Add one `ENTITY_LEGAL_NAME = "Richard Gee, an individual d/b/a Everlight Ventures"` constant; refactor `contract_generator.py`, the finder/assignment/crypto/PSA templates, and `sender_identity.json` to read from it. Purge every "Everlight Logistics LLC," "Wholesale Acquisitions LLC," and the "Marquise Smith" corruption bug. **(Free, ~1 day.)**
2. **PLANNED:** Add a pre-commit grep guard that fails on any non-canonical entity string in `contracts/` and `compliance/`. **(Free.)**
3. **PLANNED:** Get a written CA LLC reinstatement quote now (~$800 franchise tax), decide reinstate-before-Deal-1 vs. sole-prop-everywhere. **Reinstating gives you a veil against a lawsuit that can land on Deal 1; do not defer this to "post-Deal-1 revenue."**

**GATE 1 -- CHEAP-AND-NOW (free-first exhausted, then minimal spend):**
4. **PLANNED:** Wire the recipient-classifier (gov/attorney/homeowner) into `branded_mailer` + `safe_send_email` as a **fail-closed** gate. Gut the two raw `api.resend.com` senders into thin `branded_mailer` wrappers. Add sender-alias allowlist (block owner aliases as *senders*, not just recipients). **(Free, ~1 day. This and Gate 0 are a single atomic go-live gate -- never ship the deliverable address without this wired.)**
5. **PLANNED:** Authorize **$30/mo BatchSkipTracing NOW as a Deal-0 cost** -- this clears the free-first golden rule because all 4 free layers are genuinely exhausted (free tracer yields only manual URLs, phone-side blocked by Cloudflare, no programmatic free path). Run it **off-phone on e5-mother** to dodge Cloudflare. This is the actual volume unlock, not a post-Deal-1 luxury.
6. **PLANNED:** Set the CAN-SPAM physical address (~$5 to $15/mo PO box or registered-agent). **Only after #4 is wired.**
7. **PLANNED:** Restate the doctrine target: **"~1 deal in 60 to 90 days for TN"** -- re-derive from `funnel_model.py --actuals` after >=30 real sent-and-replied events. Kill the "5 deals = $5k" units error.

**GATE 2 -- PROVE THE RAILS (free, before a real seller depends on them):**
8. **PLANNED:** Dry-run one synthetic TN deal end-to-end: lead -> PSA -> Schedule A -> assignment -> $1 Stripe test invoice -> commission_ledger row -> revenue field. Write/ship `stripe_invoicer.py` (or designate manual Stripe as the Deal-1 path); make `close_deal()` call `log_commission()` and give it one real caller.
9. **PLANNED:** Confirm a SECOND Memphis cash buyer to live status (b2b phone confirm is TN-gate-permitted). Send the first qualified deal to all 4 Memphis buyers in parallel. Downgrade Chris's `state_gates.json` flag from "verified" to "cold-contacted" until a reply receipt exists.
10. **PLANNED:** Redefine agent "success" = produced artifact; add a 0-send watchdog that fires #hive-alerts Sev-1 if `outreach_count` rises while `emails_sent` stays 0 for >24h.

**GATE 3 -- EXPENSIVE-AND-LATER (deferred to real revenue):**
11. **PLANNED:** Get a **free indicative surety bond quote NOW** to learn if a thin-credit sole prop must fully collateralize the $50k face (turning a ~$1,000 premium into a $50k cash demand). Add the bond as a hard halt at deal 2 close. Cap the legal model at 2 deals until funded from Deal 1/2 proceeds. **Do not pay the $500 telemarketer reg until cold-call is actually needed (it isn't -- TN is warm-only first 3 deals).**

---

## 5. THE STRENGTHENED PLAN
*The strongest version that survives this critique.*

**Reframe the business as two products, not one dig.** The hard, defensible asset you built -- the fail-closed multi-state compliance gate (`state_gate.py`), the 8-state matrix, the eradication gate, the contract library -- is more sophisticated than most licensed brokerages have. **It is the picks-and-shovels.** The wholesale dig is the *validation lab* that proves the gate against live statutes (SB 909, a real C&D, a real BBB complaint). Run the dig to harden the asset; the day TN closes Deal 1, that closed deal becomes the case study that de-risks a **Wholesaler Compliance OS** SaaS ($49 to $149/mo) -- which scales across all 50 states with zero outreach liability because the *customer* does the sending. Don't pivot away from the lab; don't pretend the product exists yet (it would need to be built multi-tenant from scratch). Run both lanes: dig feeds shovel.

**The dig itself, strengthened:**
- **Single-buyer fix:** Buyer acquisition -- not seller-lead volume -- is the gating metric for Deal 1. Require **3 verified Memphis cash buyers** (responded=true) before scaling seller outreach. Structure the Chris relationship so Everlight locks the seller under PSA *first*, then assigns to MSH -- neutralizing the competitor-or-customer ambiguity as a contractual JV term, not a vibe. Track buyer concentration as a first-class KPI (no single buyer the only home for >50% of deals).
- **Broken-funnel fix:** Channel is the constraint, not lead count. Either fund skip-trace to lift capture toward the 12 to 15% the model assumes, OR pivot to **free direct mail** to the owner-of-record addresses already sitting in the tax data (34/35 parcels are owner-named), which sidesteps the email-capture gap entirely and is TN-compliant.
- **Target fix:** ~1 deal/quarter at current capacity, re-derived monthly from measured actuals. One Memphis assignment fee ($5.7k to $36.9k) clears the entire cost stack -- the dollar goal is real; the deal-count headline was fiction.

**The strategic question answered: the real asset is the software.** The deals prove it; the SaaS sells it. Set a hard kill/convert trigger -- **one signed PSA within 30 days of the send engine going live, or the dig demotes to maintenance-only and operator hours flow to the SaaS/consulting engines** (which scale without a $50k bond or telemarketer reg). On a risk-adjusted basis the dig is *not* the worst engine (XLM lost $500+ and is parked; Polymarket is geo-blocked from placing a single live order), it's lost $0 and has a real counterparty. But its operator-hours must be capped behind a decision gate.

---

## 6. WHAT WOULD HAVE TO BE TRUE
*The load-bearing assumptions. If any is false, the thing doesn't work, and how to test each cheaply before betting more.*

1. **A real warm seller will sign a PSA.** *Test:* Skip-trace the 34 owner-named tracker parcels off-phone (~$30), ship one canary cohort to verified TN sellers, and get **one reply** within 30 days. Zero replies after a real send = the channel is dead, not just paused. **Cost: ~$30 + 1 week.**

2. **Chris (or any Memphis buyer) will actually take an assignment.** *Test:* A b2b phone call (TN-gate permitted) for a written buy-box / proof-of-funds / signed assignment-acceptance, *before* you lock a seller. If no buyer gives a written commitment, you have a contact list, not demand. **Cost: a phone call.**

3. **The fee is collectible.** *Test:* Confirm the assignment fee disburses at the closing table as a settlement-statement line item via escrow (not a post-close Stripe invoice). Have TN counsel confirm it's RESPA-clean. Dry-run the synthetic deal end-to-end first. **Cost: counsel hour + 1 dev day.** (Verifiers downgraded the "uncollectible" claim -- the assignment contract *does* collect through escrow; the risk is the closer code drifting to an unsecured invoice. Fix the code, not the model.)

4. **The compliance gate fires fail-closed against unknown bad recipients.** *Test:* CI assertion that `branded_mailer` rejects `dstreubel@municipalfirm.com`, `partner@bigfirm.law`, and `planning@dallastx.gov` at `category=bulk`, refuse to deploy if any returns ok=True. **Cost: ~1 dev day.**

5. **One legal entity is true and propagated everywhere.** *Test:* Grep guard passes; TN counsel countersigns the single reconciled PSA + Schedule A. If you can't name one good-standing entity, you sign as sole prop with a deal ceiling + umbrella policy. **Cost: the find-replace + a counsel review.**

---

## 7. PROVENANCE
*One line per angle. Downgrades noted.*

- **Cipher Wolfe (Market & Demand)** -- Uniquely proved, with the team's *own* `funnel_model.py`, that 5 deals/mo is arithmetically impossible at the cap and exposed the "77 engaged" as IMAP newsletter artifacts. *Verifier downgrades:* the MSH duplicate-record "mis-routing" claim was **refuted** (the matcher reads only the verified record); demand single-point-of-failure held but was marked serious-not-fatal (concentration risk, not structural impossibility).

- **Penny (Financial / Unit Economics)** -- Uniquely surfaced the **5x units error** ("5 deals x $5k = $25k, not $5k"), the 4 self-billed test invoices to your own Gmail, and the verified-email denominator collapse (3,467 to ~9). *Verifier downgrade:* the "finder fee structurally uncollectible" headline was **refuted** -- it attacked the wrong contract; the assignment contract collects through escrow. Real residual is a code-vs-doctrine drift in `rex_closer.py`. Bond was downgraded fatal->manageable (premium ~$500 to $1,500, not a $50k wall, *unless* thin-credit underwriting demands collateral).

- **Theo Briggs + Justine Park (Legal / Compliance)** -- Delivered the **only FATAL finding** the other four missed: the 5-entity contract incoherence that voids SB 909 and strips the veil on Deal 1. *Verifier downgrades:* the "5 filters don't exist / gate protects one human" claim was downgraded fatal->manageable (3 of 5 filters *do* exist and are wired; real gaps are the entity-heuristic and generic attorney-domain block). The rich@ sender bypass was **confirmed** still open in two live scripts.

- **Marcus Cole (Execution / Ops)** -- Uniquely nailed the **"activity-as-success" theater** (agents at 100% success / 0 output) and proved the closed-to-paid rails are broken (`stripe_invoicer.py` missing, `close_deal()` orphaned, forked ledger). *Verifier downgrade:* the "CAN-SPAM config file doesn't exist" claim was **overstated** -- the file exists in the `Wholesale/` tree (critic searched the wrong dir), is only 8 days old not 30+, and fixing it alone unblocks nothing because the email pipe is empty upstream.

- **Solomon Vale convening (Moat / Strategy)** -- Uniquely reframed the wedge: **the software is the defensible asset, the dig is the validation lab**, sell the shovels. *Verifier downgrades:* "the SaaS engine nobody works" cited the wrong doc (SaaS-*company* brokering, a different business -- the compliance product isn't built yet); the "b2b carve-out still open" claim was **misleading** (global default true, but every non-TN state overrides it false in code); the "automation is a liability multiplier / exact Streubel hole still open" was downgraded -- the *alias-bypass* hole is closed, but the first-contact classifier gap is real.
