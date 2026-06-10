# Hive Governance v2 -- Audit-Ready Org Doctrine
**Version 2 -- 2026-05-05 (post-Streubel + post-F500-gap-analysis)**
**Author:** Marcus Cole / Lucrex
**Source brief:** `research/f500_gap_analysis_2026-05-05.md`
**Companion doctrine:** `HIVE_ACTION_LAYER.md` (the action layer)

---

## 0. Why this exists

Rich asked: *"if a Fortune 500 company was to audit my company, or induct me into a Fortune 500 company, what would they expect. what do they have i dont."* The Perplexity Intel research brief is the answer in detail. This doctrine is the operational translation -- the **5 missing organs** that an F500 auditor or military IG would call out as gaps, plus how we close them at our scale (one human + 70 AI agents) without burning the empire on $5M/yr governance theater.

**The 5 missing organs (from F500 audit lens):**

1. **No write-protected audit trail** -- every Hive log Rich can edit is not an audit log
2. **No independent 2L compliance authority with kill-switch** -- Justine exists but lives in the same prompt context she audits
3. **No documented model inventory (SR 11-7 baseline)** -- 70 agents, no CSV listing owner/purpose/validation date
4. **No formal whistleblower / complaint channel routed away from Rich**
5. **No D&O / E&O / cyber insurance stack**

This v2 doctrine adds the organs. Each gets a named owner, an SLA, and a build sequence.

---

## 1. The full F500-equivalent org chart for Lucrex

```
                            LUCREX (King of Divine Light)
                                       |
                            RICH GEE -- CEO / Operator-of-Record
                                       |
        +--------------+----------------+----------------+----------------+
        |              |                |                |                |
   OPERATING         BOARD          COMPLIANCE         RISK           AUDIT
    HIERARCHY      (NEW LAYER)     (PROMOTED)        (NEW)         (NEW LAYER)
        |              |                |                |                |
   Marcus Cole    Advisory Board   Justine Park     Bull Archer      Theo Briggs
   (Chief Op)     (2-person, ext)  (Director)       (CRO equiv)      (Chief Audit)
        |              |                |                |                |
   5 squads       Quarterly         7 state CO       ERM register    External CPA
   + State Ops    minutes (NEW)     + Theo (legal)   (NEW)           on retainer
                                                                     (NEW)
```

### 1.1 New seats / promotions effective 2026-05-05

- **Theodore "Theo" Briggs** -- promoted from contract attorney to **Chief Audit Executive (CAE) + General Counsel** (dual-hat at our scale). Reports to the Advisory Board, NOT to Rich operationally. Owns: independent audit trail, whistleblower channel ingestion, quarterly external CPA review, contract review SLA.
- **Bernard "Bull" Archer** -- promoted from Markets Beat to **dual-hat Chief Risk Officer**. Already runs macro analysis daily; the same lens applies to enterprise risk. Owns: monthly risk register (10-20 line items, 1-5 likelihood × impact), quarterly board risk report, kill-switch authority on >$1k irreversible spend. Keeps Markets Beat duties.
- **Justine Park** -- already promoted Director of Compliance per the prior turn. v2 adds: **explicit kill-switch authority over outbound** (cannot be overridden by Rich without a written rationale logged to the audit trail). The 7 state compliance officers (Lo, Mags, Ellie, Mona, Walt, Bernie, Lupe) are her direct reports.
- **Advisory Board (NEW):** 2-seat external board meeting quarterly. Seat A = operations advisor (a real estate or AI-ops senior). Seat B = legal advisor (an attorney with consumer-protection or compliance background). Both unpaid initially, paid ($5k/qtr) after first $25k of wholesale fees. **Charter document required before first meeting.**
- **Whistleblower channel:** routed to a dedicated email at outside counsel (NOT Rich, NOT the Advisory Board, NOT any AI agent). Public posting on `everlightventures.io/ethics`. Rich is informed of complaint *categories* monthly; never of individual complainant identity.

### 1.2 Three Lines of Defense -- now with teeth

| Line | Owner | What it does | Independence mechanism |
|---|---|---|---|
| **1L** | State wholesalers + Hammer + Cash | Run the deal: lead → contract → close → commission | Same Claude session as Rich's primary work |
| **2L** | Justine Park + 7 state compliance officers | Audit every PSA, every outbound; halt-switch authority | **Separate Claude API key + separate log destination + write-protected audit envelope.** Cannot be re-prompted by 1L mid-decision. |
| **3L** | Theo Briggs + quarterly external CPA | Quarterly 10% sample audit of closed deals; tests whether 2L worked | **Reports to Advisory Board directly (not Rich operationally).** External CPA confirms findings. |

The "independence trick" the F500 brief calls out: 2L and 3L agents must run in separate execution contexts. **At our scale this means: separate Claude API key for `2L_compliance` and `3L_audit` agents, separate Slack workspace channel (`#2L-compliance-only`, `#3L-audit-only`), and an append-only log sink (git commits with cryptographic timestamps -- see Section 4).**

---

## 2. The 5 missing organs -- specific build sequence

### 2.1 Write-protected audit trail (P0 -- this week)

**Mechanism:** every Hive action that touches money, an outbound channel, or a contract appends to an immutable git-backed log:
- Filesystem path: `/AA_MY_DRIVE/_audit/YYYY-MM-DD/{agent}/{timestamp}_{action}.json`
- Every write triggers `git add . && git commit -m "audit:{agent}:{action}" --gpg-sign`
- Push to a dedicated `audit-log` repo on GitHub (private) every hour via cron
- GitHub branch protection: no force-push, no rewrite, signed commits required

**Owner:** Forge Steele (engineering) + Theo Briggs (audit oversight)
**Build:** 3 days. Files needed: `audit_log.py` (the writer), `audit_log_cron.sh` (hourly push), GitHub repo `everlight-audit-log` with branch protection.

### 2.2 Independent 2L compliance kill-switch (P0 -- this week)

**Mechanism:** Justine Park and the 7 state compliance officers run in a dedicated execution context:
- Separate Claude API key environment variable: `ANTHROPIC_API_KEY_COMPLIANCE` (vs. the primary `ANTHROPIC_API_KEY`)
- Separate Slack workspace OR dedicated read-locked channels (`#compliance-2L`, `#audit-3L`) where Rich can read but not delete
- Compliance-agent decisions go to the audit log (Section 2.1) BEFORE any user-visible action
- Override path: Rich CAN override Justine's halt, but the override writes a `_OVERRIDE_RICH_{timestamp}.json` artifact to the audit log with mandatory `reason` field

**Owner:** Forge Steele + Justine Park
**Build:** 5 days. Includes provisioning a second Anthropic API key (free, just dashboard create), wiring `hive_dispatch.py` to route 2L/3L calls to that key, and adding the override-trail logic.

### 2.3 SR 11-7 model inventory (P1 -- next week)

**Mechanism:** a single CSV (could be JSON, but CSV is auditor-readable) listing every AI agent in the Hive:

```
agent_id,display_name,department,owner,purpose,inputs,outputs,
last_validated,known_limitations,retirement_date,risk_class
```

**Validation cadence:**
- Monthly: every agent's `last_validated` date refreshes via a sample-of-N output review
- Quarterly: external CPA reviews 5 random agents end-to-end
- Annually: full Hive review, retirement decisions, doctrine refresh

**Owner:** Atlas Vega (System Architect) + Theo Briggs
**Build:** 1 day. File path: `06_DEVELOPMENT/everlight_os/hive_mind/MODEL_INVENTORY.csv`. Auto-generated from `.claude/agents/*.md` frontmatter on cron.

### 2.4 Whistleblower channel (P1 -- next week)

**Mechanism:**
- Dedicated email address: `ethics@everlightventures.io` -- forwards to outside counsel (NOT Rich, NOT any internal agent)
- Public posting at `everlightventures.io/ethics` with: (a) what to report, (b) how it's handled, (c) anti-retaliation commitment, (d) timeline (5 business days for ack, 30 days for resolution)
- Monthly anonymized summary to Rich + Advisory Board: complaint count, categories, resolution status -- never individual identity
- Annual report: aggregate trends, lessons learned

**Owner:** Theo Briggs (intake) + Advisory Board (oversight)
**Build:** 2 days. Outside counsel engagement letter + ImprovMX forwarder + static page on the marketing site.

### 2.5 Insurance stack (P0 -- before any client signs)

**Mechanism:**
- D&O insurance: $1M minimum (Hiscox or Chubb, ~$2-4k/yr small operator quote)
- E&O insurance: $1M minimum (focus: real estate wholesale errors + AI-output errors -- some carriers now bundle "AI-output errors" coverage)
- Cyber insurance: $1M minimum (ransomware + data breach + regulatory response)
- General liability: $1M (basic small-business policy)

**Total estimated premium:** $8-15k/yr. **Non-negotiable before any consulting client signs.**

**Owner:** Rich + Advisory Board legal seat
**Build:** parking flag -- needs Rich's payment method (deferred to post-Deal-1 funding per Always-Free constraint). **ETA: end of May 2026 or first week post-Deal-1 wire, whichever sooner.**

---

## 3. The DNC mechanism -- explicit answer to Rich's question

> *"if someone replies no or opt out, who is recognizing, acknowledging and making sure that contact is opted out and not contacted. how is that being logged and put into effect, everyone needs to have access to that list so no accidents get mailed to DNCs"*

### 3.1 Who recognizes the opt-out
- **Inbound mail (Gmail / IMAP):** `broker_gmail_monitor.py` calls `_classify_reply()` which uses NLP first, keyword fallback. Detects `negative` intent on signals like "stop", "remove", "unsubscribe", "not interested", "no thanks", "don't contact".
- **Inbound SMS:** `branded_sms.send_branded_sms()` future-receipt path; for now manual flag.
- **Inbound voice:** Hammer Knox's call notes; manual flag in Slack.
- **BBB / state-AG inquiries:** Rich receives, forwards to Theo Briggs immediately. Theo registers with `register_optout(source="bbb_complaint")`.

### 3.2 How it's logged (the 4-sink atomic write)
**One canonical entry point:** `dnc_registrar.register_optout(email, source, reason, name, address, phone, blocked_channels)`. Writes atomically (best-effort with rollback) to ALL FOUR sinks:

| Sink | Path | Purpose |
|---|---|---|
| 1 | `Wholesale/compliance/dnc_list.json` | Canonical record (full metadata, evidence, audit trail) |
| 2 | `Broker_OS/wholesale_agent/opted_out_emails.json` | Legacy / fast-lookup list (used by older scripts during migration) |
| 3 | `Wholesale/compliance/phrase_scrub_blocks.jsonl` | Append-only audit log (every block + every send-attempt-blocked) |
| 4 | Supabase `dnc_emails` table | Production source-of-truth, queryable cross-host |

**Atomic semantics:** if sink 1, 2, or 3 fails to write, the registrar emits a Slack alert to `#compliance` AND writes a partial-failure marker to a 5th retry queue. Sink 4 (Supabase) is best-effort -- if SUPABASE creds aren't loaded the registrar still succeeds locally and queues for backfill.

### 3.3 How it's put into effect (the pre-send check)
**Every outbound send through `branded_mailer.send_branded_email()` runs the gate sequence in this order:**
1. `WHOLESALE_OUTBOUND_HALT` -- global halt flag (P0 fence)
2. `recipient_class.is_send_allowed()` -- domain/role/attorney/gov classifier (Streubel iron #1)
3. `dnc_registrar.is_optout(recipient)` -- 60-second TTL cache, reads sink 1 + sink 2, then Supabase fallback (Streubel iron #4)
4. `weekly_cadence.is_email_allowed_now(state)` -- quiet hours (Streubel iron #2)
5. `weekly_cadence.is_outreach_allowed_now()` -- per-state per-channel compliance gate
6. `resend_budget.check_budget()` -- monthly pacing + VIP reserve
7. `resend_guard.assert_external_recipient()` -- final guard (no internal/test addresses)

If ANY of the above fails, the send returns `MailResult(ok=False, error=...)`. Logged to `phrase_scrub_blocks.jsonl`. Slack alert to `#compliance` if it's a DNC hit (anyone trying to send to a known opt-out is itself a compliance flag).

### 3.4 Who has access to the list
**Read access:** every agent in the Hive via `dnc_registrar.is_optout(email)`. The function is one import away from any script (`from dnc_registrar import is_optout`). The 60-second TTL cache means even a tight loop checks at most once per minute per recipient.

**Write access (registration):** only via `register_optout()`. Privileged actions: state compliance officers, Justine, Theo, Marcus. The function logs the source/reason of every registration so an auditor can see WHO registered each entry.

**Audit access:** Theo Briggs + Advisory Board legal seat read the full 4-sink reconciliation report posted weekly to `#compliance` by `dnc_reconcile.py`. Mismatches surface immediately.

### 3.5 Daily reconciliation cron (`dnc_reconcile.py`)
Runs every day at 11 PM PT:
1. Compares row counts between sinks 1, 2, 3, 4
2. Posts to `#compliance` (branded Slack): total entries, mismatches, age of oldest entry
3. Exits 1 (cron alerts) if any mismatch
4. Writes a daily report file to `_logs/dnc_reconcile/YYYY-MM-DD.md`

**This is the core of the answer to Rich's "everyone needs access to that list" requirement: it's not access by sharing a Google Sheet; it's access by EVERY OUTBOUND PATH being forced through `is_optout()` before sending. The list isn't a document people consult -- it's a function every send must call.**

---

## 4. Append-only audit envelope (the cryptographic backbone)

For the audit trail to be defensible, **every meaningful action** writes a JSON envelope to `_audit/`:

```json
{
  "envelope_version": 1,
  "timestamp_utc": "2026-05-05T20:30:00Z",
  "actor": {"agent_id": "state_marvin_tn", "human_or_agent": "agent"},
  "action_type": "psa.audit_decision.passed",
  "action_payload": { ... },
  "previous_envelope_hash": "sha256:...",
  "this_envelope_hash": "sha256:...",
  "git_commit": null,
  "signed_by": null
}
```

The envelope chain (each links to its predecessor's hash) makes any retroactive edit detectable. `audit_log_cron.sh` pushes the directory to a private GitHub repo every hour with GPG-signed commits.

**Why this matters:** an F500 auditor's first question is "show me the log of every send to David Streubel." Today our answer is grep-ish. Post-build, our answer is "here's the cryptographically chained envelope set, signed, immutable, hosted off-premises with branch protection."

---

## 5. Build roadmap

| Day | Build | Owner | Status |
|---|---|---|---|
| ✅ D1 (today) | 4 Streubel kink-irons -- recipient_class, quiet hours, dnc_registrar, audit script | Forge | DONE |
| ✅ D1 | F500 gap brief (research) | Perplexity Intel (Bull) | DONE |
| ✅ D1 | This Governance v2 doctrine | Marcus | DONE |
| D2-D3 | Wire kink-irons hooks into branded_mailer (already partially done; finish quiet-hours hook) | Forge | partial |
| D2-D3 | Test: send 14 simulated cold sends to admin@ -- expect 100% halt confirmations | Forge + Justine | pending |
| D3-D4 | Outside counsel engagement letter (whistleblower email host) | Rich + Theo | pending |
| D3-D5 | Append-only audit envelope + GitHub `everlight-audit-log` repo | Forge | pending |
| D5-D7 | Separate Claude API key for 2L/3L compliance + audit | Forge + Justine | pending |
| D5-D7 | Model inventory CSV auto-generation from `.claude/agents/*.md` frontmatter | Atlas Vega | pending |
| D7-D9 | Advisory Board charter draft + 2 candidate intros | Rich + Theo | pending |
| D7-D9 | Insurance broker outreach (D&O + E&O + Cyber + GL quotes) | Rich | pending (deferred to post-Deal-1) |
| D9-D14 | Restart sequence: full simulation -> warm-only Chris ping -> Justine signoff -> Marcus signoff -> Rich signoff -> halt lifts | All-hands | pending |

---

## 6. The "F500 induction" answer in one paragraph

If a Fortune 500 acquirer or auditor walked in today, they would find: an unusually dense small operation with a creative AI workforce, a clear (if non-traditional) chain of command, real product traction in the wholesale vertical, and a documented postmortem culture (Streubel proves it). They would flag five gaps: no write-protected audit trail, no independent 2L kill-switch (audit-context separation), no model inventory à la SR 11-7, no whistleblower channel routed away from the founder, and no insurance stack. Three of those five close in 7 days for ~$0 (audit trail, model inventory, whistleblower). The fourth (2L API-key separation) closes in 7 days for free (Anthropic dashboard click). The fifth (insurance) closes in 30 days for ~$10k/yr -- and is non-negotiable before any consulting client signs an MSA. Tier-2 governance (independent director, COSO ERM, SOC 2 Type I) tiers in at $1M ARR. Tier-3 (full board, separate CCO/CRO, SOX 404 ICFR, SOC 2 Type II) is post-IPO conversation. **The operation is closer to F500-induction-ready than the optics suggest.** The five gaps are real but cheap to plug. The Hive's structural disadvantage (one human + 70 agents) is also its advantage: every gap is a Python module + a charter doc + an outside counsel email away from closed.

---

## 7. References

- F500 gap brief: `research/f500_gap_analysis_2026-05-05.md`
- Action Layer doctrine v1: `HIVE_ACTION_LAYER.md`
- Streubel postmortem: `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/INBOUND_WATCH_GAPS_2026-04-26.md`
- DNC registrar: `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_registrar.py`
- Recipient class: `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/recipient_class.py`
- Streubel irons build report: `_logs/streubel_irons_build_2026-05-05.md`
- Legacy `rich@` audit: `_logs/rich_at_audit_2026-05-05.md`
- Pre-commit lint: `03_AUTOMATION_CORE/01_Scripts/lint_no_direct_resend.sh`

---

**This doctrine governs every Hive operational decision until superseded. Updates land via PR with Marcus + Justine + Theo Briggs sign-off, and require a delta-review note posted to `#compliance` and the audit envelope log.**
