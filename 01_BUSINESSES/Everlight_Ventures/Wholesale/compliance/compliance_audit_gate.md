# Compliance Gate Audit -- Everlight Intel Center per-state layer
Auditor: Justine Park | Date: 2026-05-12 | Status: HONEST RED-TEAM

## Verdict: 6.5 / 10 -- gate is real but porous

---

## 1) Bypass vectors -- can investigations skip business_purpose?

YES. Three holes.

**A. Direct orchestrator import (CRITICAL).** `osint_api.orchestrator.run_investigation()` and `run_investigation_sync()` accept `business_purpose: str = ""` with a default empty string and NEVER validate it. Anyone (including peer agents, scripts in /scripts_internal, suites) who imports the module bypasses both the FastAPI 400-gate and the CLI input-prompt. The compliance_log only writes the entry that the CALLER chose to log; the orchestrator itself does not call `log_action` -- look at orchestrator.py lines 125-147, the `final` payload is written to disk and the HTML snapshot rendered with `business_purpose=""`. No log row is created from inside the orchestrator. Fix: assert at the top of `run_investigation` -- `if not business_purpose.strip(): raise ValueError(...)`. This is the single most important fix.

**B. CLI accepts a single space.** `intel investigate "X" --purpose=" "` passes `purpose.strip()` checks because the prompt fallback only fires when `purpose == ""` (post-strip). Wait -- re-read line 1349: `if not purpose: sys.exit(...)` runs AFTER the strip on 1346, so " " is caught. OK, the CLI is tight. Withdraw this finding.

**C. API pre-strip is fine, but the `viewer` query param on `/report/{inv_id}` is unauth.** Anyone hitting `/report/abc?viewer=Bob` writes "Bob" into the audit log as the actor. The API has no auth at all (FastAPI app on :8677, no Depends, no token). Anyone on the box or tunnel can mint compliance_log entries with any actor name. This poisons the audit trail. Fix: bind to 127.0.0.1 only + add a shared-secret header check.

## 2) Unknown-state handling

PASS, with one display nit. `legal_state.state_rules_for("ZZ")` returns `covered=False` + `warning="STATE UNKNOWN -- consult Justine before any contact. No outreach permitted."`. The renderer's `_state_legal_panel` correctly emits the red `⛔ UNKNOWN STATE` banner (report_renderer.py lines 116-123). Verified by code path: `not state_rules.get("covered")` triggers the unknown branch BEFORE the regular hard-block branch.

NIT: the channel matrix table is empty for unknown states (channels_allowed = {}), so the operator sees "ALLOWED/BLOCKED" rows for nothing. Should display a single full-width "all channels blocked pending state confirmation" row. Cosmetic, not gate-failure.

## 3) DNC + report interaction -- THIS IS BROKEN

The OSINT-side report does NOT consult `Wholesale/compliance/dnc_list.json`. Confirmed three ways:

- `grep -rn "dnc_list\|load_dnc\|is_on_dnc" 06_DEVELOPMENT/everlight_os/intel_center/` returns ONLY a citation of `state_dnc_list` flag in legal_state.py (different concept -- that is "does the state maintain its own DNC registry").
- `profile_synthesizer.py` lines 68-73: `dnc_blocked = bool(payload.get("dnc_blocked"))` -- it only honors a flag the orchestrator/investigators put in the payload. The orchestrator never sets it. No investigator queries the DNC file.
- The comment on line 69 admits it: `"the wholesale enricher writes it separately"`. So if you run `intel investigate "David Streubel"`, the rendered HTML has NO DNC banner. Streubel will be profiled, his BBB-complainant property surfaced, and the report will read "no restrictions" because the DNC check lives in a parallel system.

This is a real-money risk. We had a BBB-threat eradication on 2026-05-04 specifically because we re-contacted a "no". An OSINT report with no DNC banner gives an operator green light to re-engage.

Fix: add `dnc_check.py` to osint_api/ that loads dnc_list.json once (lru_cache), normalizes name + email + address, and the orchestrator calls it BEFORE running investigators. If matched: set `dnc_blocked=True`, `dnc_reason=...` on the final payload, AND write a `policy_violation` row to compliance_log if anyone tries to view the report. Block render-time, not just display-time.

## 4) Right-to-purge gap (CCPA / GDPR Article 17)

CRITICAL gap. No `intel purge-target <name>` exists. To honor a deletion request manually today the operator would need to remember 7+ surfaces. Required purge set:

- `cache/investigations/*.json` -- DELETE rows where target matches OR results contain matching email/phone/address.
- `cache/reports/*.html` -- DELETE matching investigation_id.html files.
- `database/investigations.sqlite` -- DELETE FROM investigations WHERE target ILIKE...; also any FTS shadow tables.
- `cache/compliance.sqlite` (compliance_log) -- KEEP for legal hold (7-year retention is the defensible standard for compliance audit trails). REDACT PII columns instead: blank `target`, `notes`, `state_rules_consulted`; keep `id`, `ts`, `action`, `business_purpose`. Log the redaction itself as a `purge` action with the original target hash.
- `01_BUSINESSES/Everlight_Ventures/Wholesale/leads_db.sqlite` -- DELETE leads + clear `intel_enrichment_json`. Already covered by the DNC eradication script per the May-4 fix; verify the purge tool calls it.
- `Wholesale/compliance/dnc_list.json` -- ADD an entry (do not remove -- a purge request is implicit DNC).
- `live_log` records and any Blinko notes containing the target name (check `_logs/blinko_lite.db` + e5-mother Blinko via API).
- Any `audit_reports/*.md` or `audit_reports/*.html` snapshots -- redact target name, keep aggregate counts.

NOT to purge: `articles.sqlite` (sources, not targets -- correct) and the compliance_log rows themselves (legal hold).

The script must be transactional: write a `purge` row first with the original target hash, do all deletions, write a confirmation row. If any step fails, document partial state in the confirmation row.

## 5) Overall posture: 6.5 / 10

What works: API gate + CLI gate + immutable append-only log + per-state rules pulled from canonical state_gates.json + UNKNOWN STATE banner renders + watermarking on report + 0o600 file perms.

What does not: orchestrator-level bypass, unauth API actor spoofing, DNC blind spot, no purge tool.

**The single +1 fix:** assert business_purpose at the orchestrator entry point AND wire the DNC check into the orchestrator preflight. One commit, two functions, kills three of the five findings above. That alone takes the score to 7.5.

Aigoo. Build it before next week's audit.
