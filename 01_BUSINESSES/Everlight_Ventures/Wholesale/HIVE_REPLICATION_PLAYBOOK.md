# Hive Replication Playbook -- AWWP Pattern Reuse

**Purpose:** the 12-phase Autonomous Wholesale Workflow Pattern (AWWP) is buyer-agnostic, market-agnostic, source-agnostic. The phases never change. Three sets of *parameters* change. This file tells the Hive what to swap when.

**Canonical pattern:** `Wholesale/AUTONOMOUS_WORKFLOW_PATTERN.md`
**Canonical orchestrator:** `03_AUTOMATION_CORE/01_Scripts/wholesale_pipeline_orchestrator.py`

---

## The three replication triggers

### Trigger A -- new buyer added (after Chris)

Cloning the workflow for buyer #2, #3, #N. Pattern is identical -- buyer sees a deal package, signs Assignment, wires GFAD, closes through their preferred title firm. Parameters that change:

| Parameter | Default (Chris) | Where to update | Who owns |
|---|---|---|---|
| Buy box (zips, type, build year, condition, price tiers) | Memphis 15z + Little Rock 9z, 1940+, $30-60k sweet spot | `Wholesale/buyers/{slug}/buy_box.json` | Penny Vance |
| MAO formula | "ARV * 0.65 - rehab - my fee" (assumed; ask for confirmation when first deal lands) | `Wholesale/buyers/{slug}/mao_formula.json` | Penny + Filter Banks |
| Decision SLA | unspecified -- want 48hr written turnaround | `Wholesale/buyers/{slug}/sla.json` | Marcus Cole |
| Title firm | Mid-South Title (Memphis), Chris-aligned | `Wholesale/buyers/{slug}/title_firm.json` | Henry Knox |
| Assignment Agreement template | Clauses 2.1, 2.4, 2.6 | `Wholesale/contracts/templates/assignment_template_v1.md` | Henry |
| GFAD amount | $500-$1,500 | `buyers/{slug}/gfad_default.json` | Henry |
| Backup buyers (if primary unresponsive >36hr) | top-2 reactivation list | `Wholesale/buyers/backup_pool.json` | Penny |

**What stays canonical:** every phase 1-12, the Operator-Truth gating logic, the orchestrator, the email/Slack/contract pipelines, the 25/day cap, the no-auto-fire-to-humans boundary.

**Cloning command:**

```bash
python3 03_AUTOMATION_CORE/01_Scripts/wholesale_buyer_clone.py \
  --slug "atlanta_marcus_holdings" \
  --base "chris_midsouth"     # copies Chris's parameter set, then we edit
```

(Buyer-clone script is a 30-min build when buyer #2 lands. Pattern is: load `buyers/chris_midsouth/*.json`, write same files under new slug, flip the buy-box constants. Marcus dispatches Henry to build.)

---

### Trigger B -- new market entered (Memphis -> next metro)

Cloning into a new metro. Pattern is identical -- intake, parse, intel, skip-trace, compliance, email, reply, PSA, assign, title, wire. Parameters that change:

| Parameter | Default (Memphis TN) | Where to update | Who owns |
|---|---|---|---|
| Lead source URL | Shelby Tax Sale CSV | `Wholesale/lead_sources/{metro}/source.json` | Rex Blackwell |
| Assessor portal URL + parser | `assessormelvinburgess.com` + `parse_assessor_mhtml.py` | `Wholesale/lead_sources/{metro}/parser.py` (sub-class of base parser) | Henry / Forge |
| State compliance gates | TN: warm-only first 3 deals, cold-call BLOCKED, SB 909 wholesaler disclosure required | `Wholesale/compliance/state_gates.json` (already multi-state) | Justine Park |
| Title firm options | Mid-South Title (Memphis) | `Wholesale/title_firms/{metro}/firm_list.json` | Shield + Henry |
| Probate court portal | Shelby County Probate | `Wholesale/lead_sources/{metro}/probate.json` | Cipher Wolfe |
| Local Slack channel | `#wholesale-deals` (single feed for now) | `slack_routing.yaml` -- add `wholesale-deals-{metro}` if volume warrants | Marcus Cole |
| Phone hour buffer | 8am-9pm CT (Memphis) | `state_gates.json` (auto applies per owner timezone) | Justine |

**What stays canonical:** every phase 1-12, the orchestrator detection logic, the 25/day cap (per market or aggregated -- TBD when 2nd market lands), the contract generators (state-routed already).

**Operator-Truth check before clone:** the new state's compliance gates MUST be loaded into `state_gates.json` BEFORE the orchestrator processes a single lead from that metro. Justine's pre-flight: search the state's wholesaler disclosure law, foreclosure-relief restrictions, cold-call/SMS rules, DNC registry. No outreach until gates land.

---

### Trigger C -- new lead source integrated (beyond tax-sale CSV)

Cloning the workflow into a new source -- Zillow FSBO, Craigslist, ATTOM cache, public records list-pulls, SOS LLC dissolution pull, code-violation list, etc. Pattern is identical from phase 4 onward -- intel, skip-trace, compliance, email, etc. Parameters that change at phases 1-3:

| Parameter | Default (Shelby tax-sale CSV) | Where to update | Who owns |
|---|---|---|---|
| Source ingest | `pipeline_intake.py` reads Shelby CSV | `Wholesale/lead_sources/{source}/ingest.py` (sub-class) | Rex |
| Source-specific filters | Memphis + Chris's 15z + status=new + TS2202 priority | `Wholesale/lead_sources/{source}/filter.py` | Filter Banks |
| Source-specific buy-box pre-screen | Marquise's lot/SFR/year-built rules | sub-class of `Wholesale/scoring/lead_prioritizer.py` | Filter |
| Phase-2 enrichment path | Playwright on assessormelvinburgess.com | per source -- some sources (Zillow) already include owner data | Henry |
| Phase-3 buy-box gate | `chris_check` field | source-specific verdict logic, then merges into the same gate | Filter |

**What stays canonical:** every phase 4-12. The orchestrator does not care where the lead came from -- it cares about FS artifacts.

**Operator-Truth check:** sources that fingerprint the workflow (e.g. Zillow scrape that gets us banned) need rate-limit + UA rotation before turn-on. Justine + Cipher do a free-path scan first -- never pay $99/mo for a list when public records suffice.

---

## What the Hive does autonomously when a trigger fires

For each trigger A/B/C, Marcus Cole (Chief Operator) runs this order:

1. **Discover the gap.** A query lands ("Marquise just confirmed buyer #2") -- Marcus reads the state of `buyers/`, sees the empty slot.
2. **Dispatch parameter-fill agents in parallel.** Single message, multi-Agent block. For trigger A: Penny pulls buy-box from email/written intake; Filter computes MAO formula; Henry confirms title firm; Marcus drafts SLA.
3. **Run cross-check.** Cipher reviews Penny's buy-box for completeness; Justine reviews compliance fit (state gates if buyer wants out-of-TN deals); Filter checks MAO arithmetic.
4. **Synthesize into the JSON files.** Marcus writes the canonical `buyers/{slug}/*.json`. Provenance (which agent contributed which field) noted in `_provenance.json`.
5. **Ping #war-room.** Branded Slack with the new buyer slug + parameter set. Marquise reviews.
6. **First test deal.** Orchestrator routes the next eligible lead through phases 1-7 (or phases 9+ for an existing PSA-signed deal looking for a buyer) using buyer #2's parameters. Output is a draft deal package in pending_approval/. Marquise approves.
7. **Log to Blinko + Hive Dashboard.** Pattern reuse is the whole point -- the next trigger should be cheaper because the playbook tightens with each cycle.

---

## What the Hive does NOT do autonomously

Hard boundary. Marquise approves, every time:
- First outbound email to a new buyer
- First outbound email to any seller
- Any wire instruction broadcast or change
- Any contract send-for-signature
- Any new state's compliance gate ON-switch (Justine drafts; Marquise approves)
- Any new lead source ON-switch (Rex / Filter draft; Marquise approves)

Hive runs intel, skip-trace, MX verify, contract DRAFTING, internal Slack, internal scheduling, `pending_approval/` queueing, ledger updates -- no human-facing send.

---

## How the orchestrator self-extends

When a new buyer/market/source clone lands in `buyers/{slug}/` or `lead_sources/{slug}/`, the orchestrator picks it up automatically on the next pulse -- it scans by file presence, not config. There is no central buyer registry to update. **Pattern is in the file system. That's the registry.**

Three rules the orchestrator enforces, no exceptions:
1. No outbound human-facing send without `email_approved.json` artifact (Marquise drops this file after reading the draft).
2. No PSA generation without `psa_approved.json` (Henry drafts; Marquise approves).
3. No phase advance past phase 6 without compliance_check.json verdict=PASS.

Self-test: `python3 wholesale_pipeline_orchestrator.py --dry-run --cap 0`. If a phase claims PASS but a precondition is missing, the dry-run flags it. Operator Truth doctrine -- the orchestrator does not lie about its own state.

---

## When this playbook gets out of date

Marcus reviews this file on the **first business day of every month** AND on every trigger A/B/C event. Edits go through the same diff-and-merge cross-check cycle the rest of the Hive uses (3+ agents review; Marcus synthesizes; provenance recorded).

Pattern owns the Hive. Hive does not own the pattern.
