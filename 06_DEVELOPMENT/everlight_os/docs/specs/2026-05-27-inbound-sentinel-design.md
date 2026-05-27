# Inbound Sentinel -- Design Spec

**Date:** 2026-05-27
**Author:** Lucrex (Claude CLI) for Rich
**Status:** Approved (design); pending implementation plan
**Trigger:** Cold inbound email from `ben@anyipit.com` ("Commercial OPS @ anyIP") reached
`1m.rich.gee@gmail.com` on 2026-05-27 06:24 UTC asking about the public
`EverlightVentures/everlight-ventures` repo and its "proxy-broker" layer. No Hive agent
surfaced it. Root cause: no monitor watches for *strangers who contact us first*.

---

## 1. Problem

The Hive's email monitors are keyed to **known relationships**:

- `broker_gmail_monitor.py` -- reacts only to sender domains already in the seller DB
  (`SELLER_DOMAINS`), and only on `sage@everlightventures.io`.
- `gmail_label_router.py` / `phone_imap_poller.py` -- label replies from people *we* emailed.
- `critical_email_monitor.py` -- matches billing/legal/security senders (Oracle, Stripe, IRS...).
  **Also currently broken**: its cron has run every 5 min but logs
  `"missing GMAIL_USER or GMAIL_APP_PASSWORD"` since at least 2026-05-26. It reads the wrong
  env vars (`GMAIL_USER`/`GMAIL_APP_PASSWORD`) while the working creds are
  `GMAIL_IMAP_USER`/`GMAIL_IMAP_PASS`. It is blind right now.

A **stranger who reaches out first** -- vendor pitch, partnership feeler, investor curiosity,
press, recon probe, or job inquiry -- matches none of these filters and is invisible.

The anyIP email is the canonical case: a real human, unknown domain, referencing a **public
Everlight asset**, asking a fishing question ("how important is that proxy layer to you?").
Low threat (it is SDR sales), but it also revealed that the **public GitHub org exposes infra
hints** and is being scraped by strangers -- an opsec signal worth catching every time.

## 2. Goal

A monitor that detects **inbound email from strangers that concerns Everlight**, classifies and
enriches it, surfaces it within minutes, and -- within strict safety scoping -- either auto-replies
(low-risk noise) or auto-drafts a reply for one-tap approval (everything that matters).

### Non-goals (YAGNI)
- Not replacing `broker_gmail_monitor` (known-seller replies) or `critical_email_monitor`
  (billing/legal alerts). Sentinel fills the *stranger* gap and **fixes** the shared credential
  bug those monitors also need fixed.
- No new outbound *campaign* capability. Sentinel only ever *responds* to mail that arrived.
- No CRM build. A JSONL ledger + existing Slack/Blinko logging is enough for v1.

## 3. Decisions (locked with Rich, 2026-05-27)

| Decision | Choice |
|---|---|
| Inbox scope | **Every Everlight address** (personal Gmail + all @everlightventures.io aliases) |
| Action on detect | **Auto-classify + auto-reply, SCOPED** (see below) |
| Triage depth | **Full enrichment** (categorize + domain/company lookup + intent score + opsec check) |

### Scoped auto-reply (the key safety rule)
Blanket auto-reply to strangers conflicts with hard law (every email must clear
`eradication_gate` + `branded_mailer` + voice-register; the Lucrex full-proactive-authority law is
scoped to *moltbook*, not email) and re-creates the Streubel auto-send failure mode. Therefore:

| Category | Action |
|---|---|
| `vendor_pitch` (generic), `opt_out` request | AUTO-REPLY -- safe templated response, leaks nothing, all rails enforced |
| `partnership`, `investor`, `press`, `recon_probe`, `job`, `ambiguous` | AUTO-DRAFT a Gmail draft for one-tap approve/send -- never auto-sent |

Rationale: auto-replying to a recon-probe or spoofed address confirms the address is live +
monitored and risks leaking the exact thing being fished for. Auto-reply is reserved for cases
where a canned, content-free brush-off is the correct and safe response.

## 4. Architecture

A single new module `03_AUTOMATION_CORE/01_Scripts/inbound_sentinel.py`, run on a 5-min cron,
piping each inbox through five stages. **Reuse-first** -- Sentinel is mostly glue:

```
IMAP fetch --> Stranger filter --> Classify + enrich --> Opsec check --> Action router
   |                |                    |                    |               |
 (shared        (new logic)      neuromorphic.nlp_engine   (new logic)    branded_slack
  cred fix)                      + optional LLM            vs confid.     + ntfy push
                                                           doctrine       + eradication_gate
                                                                          -> branded_mailer
                                                                          -> recipient_register
                                                                          -> confidentiality gate
```

### Stage 1 -- Fetch
- One shared IMAP helper (extract the duplicated logic in `critical_email_monitor` +
  `broker_gmail_monitor` into `content_tools/imap_fetch.py`).
- **Credential fix:** read `GMAIL_IMAP_USER` / `GMAIL_IMAP_PASS` / `GMAIL_IMAP_HOST` from
  `03_AUTOMATION_CORE/03_Credentials/.env`. Sentinel and the repaired `critical_email_monitor`
  share this helper so the bug is fixed once.
- **"Every Everlight address" realism:** the 42 @everlightventures.io ImprovMX aliases forward
  *into* the Gmail mailbox(es). v1 connects to the personal Gmail (and `sage@` if separate) and
  reads `Delivered-To` / `X-Original-To` headers to know **which alias was hit**, rather than
  opening 42 IMAP connections. *Implementation must verify the forwarding topology first.*

### Stage 2 -- Stranger filter
An email is **stranger-inbound** when ALL hold:
1. Sender domain NOT in known seller/buyer/contact sets (reuse `SELLER_DOMAINS` loader + a
   `known_contacts.json`).
2. NOT a billing/service alert (defer those to `critical_email_monitor`'s patterns).
3. NOT bulk marketing -- detected via `List-Unsubscribe` header, `Precedence: bulk`, ESP markers,
   and promo heuristics. **This is the noise gate** that keeps the ~90% newsletter flood out
   (the unread inbox is dominated by Carnival, beehiiv, Coursera, etc.).
4. Looks person-to-person: low-volume sender domain, personalized body (names a specific repo,
   page, or person), or addressed to a human-facing alias (hello@, vaughn@, etc.).

Output: keep #4-passing strangers; everything else is logged-and-dropped (seen-set dedup).

### Stage 3 -- Classify + enrich
- **Category** (one of): `sales_pitch | partnership | investor | press | recon_probe | job | other`.
  Primary: `neuromorphic.nlp_engine`; optional LLM second-pass for ambiguous cases
  (OpenRouter per `openrouter_fallback` skill to control burn).
- **Enrich:** domain/company lookup (WHOIS + homepage title; passive/legal), intent score, and
  **which public Everlight asset they referenced** (parse for repo paths, domains, page names).

### Stage 4 -- Opsec check
If the body cites a specific public asset (e.g. `everlight-ventures` repo, a "proxy-broker"
component, an internal-sounding term), flag **what is exposed** and cross-reference the
confidentiality doctrine (`moltbook_confidentiality_gate` pattern). Emits an `opsec_flag` on the
alert so Rich sees "your public repo is leaking X" the moment it happens.

### Stage 5 -- Action router
- **Always:** append to `_logs/inbound/sentinel.jsonl`; ntfy push; branded Slack card to
  `#hive-alerts` (`branded_slack.post_branded_slack`, category `intel`) with sender, category,
  enrichment, opsec flag, and recommended action. High-stakes categories
  (`partnership|investor|press`) additionally ping `#ceo-brief`.
- **Reply path (scoped):**
  - Low-risk -> auto-reply via `eradication_gate -> branded_mailer.send_branded_email
    (budget_category="vip_reply", recipient_profile=...) -> recipient_register` voice classifier,
    with the **confidentiality gate** asserting the body leaks no internal state.
  - High-stakes -> build a **Gmail draft** (`create_draft`) in the routed persona's voice; no send.
- **Persona routing:** `sales_pitch`->brush-off template; `partnership`/`investor`->Vaughn;
  `press`->content director; `job`->ops; `recon_probe`->draft + opsec flag, never auto-reply.

### State, host, schedule
- Dedup by `Message-ID` in `_logs/inbound/sentinel_seen.json` (same pattern as
  `critical_email_monitor`).
- **Host:** e5-mother (always-on, will not miss while the phone dozes); phone cron as fallback.
  Deploy via `deploy_to_oracle.sh` list.
- **Cron:** every 5 min, one-shot (`inbound_sentinel.py --once`).

## 5. Components & interfaces

| Unit | Purpose | Depends on |
|---|---|---|
| `content_tools/imap_fetch.py` | Shared IMAP fetch + header parse; fixes cred bug | stdlib `imaplib`, `.env` |
| `inbound_sentinel.py` | Orchestrates 5 stages; CLI `--once` / `--daemon` | imap_fetch, nlp_engine, branded_*, eradication_gate |
| `sentinel_classifier.py` (or inline) | Category + enrichment + intent score | nlp_engine, optional OpenRouter |
| `sentinel_filter.py` (or inline) | Stranger + bulk-marketing filter | known_contacts.json, SELLER_DOMAINS |
| `known_contacts.json` | Allow-list of people/domains we already know | -- |
| `_logs/inbound/sentinel.jsonl` | Append-only ledger of every triaged stranger | -- |

Each is independently testable: the filter takes a parsed-email dict and returns
keep/drop+reason; the classifier takes body+headers and returns `{category, intent, enrichment,
opsec_flag}`; the router takes a classified record and performs side effects.

## 6. Error handling
- IMAP login failure -> log, ntfy a one-line ops ping, skip cycle (never crash the cron).
- Classifier/LLM failure -> fall back to keyword classifier (never block the alert).
- Any send (`branded_mailer`) failure -> degrade to draft + Slack note (never silent -- per
  `prove_real_not_simulated` + `fail_loud_with_it_auto_repair`).
- Confidentiality-gate or eradication-gate block -> hard stop the reply, alert only.

## 7. Testing
- Unit: stranger-filter truth table (anyIP email = keep/`recon_probe|sales_pitch`; a Carnival
  newsletter = drop/bulk; a known seller reply = drop/known; a Stripe alert = drop/critical-defer).
- Unit: classifier categories on fixture emails per bucket.
- Integration (dry-run flag): full pipe on a fixture mailbox, asserting **no real send** and a
  correct draft/alert. Auto-reply path tested behind `--dry-run` so no email leaves during tests.
- Receipts: a live `--once` run against the real inbox surfacing the anyIP thread as the
  acceptance proof (per `prove_real_not_simulated`).

## 8. Rollout
1. Build `imap_fetch.py` + repair `critical_email_monitor` credential path (unblocks the
   existing monitor as a side benefit).
2. Build filter + classifier with fixtures (TDD).
3. Wire router with `--dry-run` default; verify drafts/alerts on the real anyIP thread.
4. Flip auto-reply on for low-risk categories only; deploy to e5-mother cron.
5. Log session to Blinko; update LIVING_PUNCHLIST.

## 9. Open items to verify during implementation
- ImprovMX->Gmail forwarding topology (one mailbox vs. several) -- drives Stage 1.
- Whether `sage@everlightventures.io` has a distinct IMAP mailbox or also forwards.
- Confirm `recipient_register.py` + a reusable confidentiality gate exist for the email path
  (moltbook gate is the reference pattern).
