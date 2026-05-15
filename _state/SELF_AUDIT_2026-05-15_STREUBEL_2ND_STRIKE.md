# SELF-AUDIT -- Streubel 2nd-Strike Discrepancy Report
**Date:** 2026-05-15 (PT)
**Trigger:** David A. Streubel received a 2nd unwanted outreach despite being on the DNC list across 3 separate storage locations since 2026-05-05. Email body was also un-branded plain text (Resend raw POST, not `branded_mailer`).
**Author:** Lucrex (Claude). No justifications. Facts and fixes only.

---

## TL;DR -- Two failures stacked

1. **DNC failure.** Streubel is in `dnc_list.json`, `opted_out_emails.json`, AND `recipient_classifier.py`. None of them were consulted by the script that sent today's email.
2. **Brand failure.** The email skipped `branded_mailer.send_branded_email()` -- it went direct to `api[.]resend[.]com` -- so no gold template, no wordmark, no Playfair font, no Piper/Marvin/Vaughn agent attribution block. It looked like a Yahoo Mail one-liner.

Both failures have the same root cause: **the canonical send path (`branded_mailer`) is not enforced. 13 wholesale_agent scripts bypass it and call Resend directly.**

---

## A. Scripts that BYPASS `branded_mailer` (direct `api[.]resend[.]com` POSTs)

Every one of these can send an email without invoking the gold template OR the DNC gate. **Today's send came from #13 (`rex_belfort_sequence.py`).**

| # | File | Path | Risk |
|---|------|------|------|
| 1 | `rex_belfort_sequence.py` | wholesale_agent/ | **THIS IS THE CULPRIT.** Line 174 `requests.post("https://api[.]resend[.]com/emails"...)`. Day-2 follow-up template (line 64) is the exact body Streubel got. |
| 2 | `rex_7touch_sequence.py` | wholesale_agent/ | 7-day cadence. Same risk. |
| 3 | `rex_negotiator.py` | wholesale_agent/ | Modified today per git status. Direct API. |
| 4 | `rex_daily_run.py` | wholesale_agent/ | Daily cron. |
| 5 | `rex_sdr.py` | wholesale_agent/ | Sales dev rep loop. |
| 6 | `rex_autonomous.py` | wholesale_agent/ | "Autonomous." Bypasses brand. |
| 7 | `rex_batch_offers.py` | wholesale_agent/ | Batch sends. |
| 8 | `rex_buyer_acquisition.py` | wholesale_agent/ | Buyer-side. |
| 9 | `rex_stop_handler.py` | wholesale_agent/ | **Irony: the STOP handler itself bypasses.** |
| 10 | `rex_utils.py` | wholesale_agent/ | Utility shared across rex_*. |
| 11 | `hive_outreach.py` | wholesale_agent/ | Top-level outreach. |
| 12 | `lis_pendens_pipeline.py` | wholesale_agent/ | Foreclosure pipeline. |
| 13 | `piper_outreach_templates.py` | wholesale_agent/ | Piper template engine. |
| 14 | `surplus_outreach_templates.py` | wholesale_agent/ | Surplus funds. |
| 15 | `consulting_outreach.py` | AI_Consulting/outreach/ | Different LOB but same bypass pattern. |
| 16 | `hive_health_monitor.py` | 03_AUTOMATION_CORE/01_Scripts/ | Alerting (system mail, lower risk but still bypass). |
| 17 | `hive_god_mode.py` | 03_AUTOMATION_CORE/01_Scripts/ | Master orchestrator. |
| 18 | `mcp_health_monitor.py` | 03_AUTOMATION_CORE/01_Scripts/ | MCP heartbeat alerts. |

## B. Scripts using raw `smtplib` (older SMTP path, also bypasses everything)

| File | Path |
|------|------|
| `broker_daily_orchestrator.py` | 03_AUTOMATION_CORE/01_Scripts/ |
| `wholesale_deal_engine.py` | 03_AUTOMATION_CORE/01_Scripts/ |
| `funnel_nurture.py` | 03_AUTOMATION_CORE/01_Scripts/ |
| `broker_os/server.py` (MCP) | 06_DEVELOPMENT/mcp_servers/broker_os/ |
| `gmail_scripts/send_gmail.py` | 03_AUTOMATION_CORE/01_Scripts/gmail_scripts/ |

## C. Scripts using `branded_mailer` CORRECTLY (doctrine-compliant)

30+ scripts in `Wholesale/`, `Broker_OS/`, and `03_AUTOMATION_CORE/01_Scripts/` already use the canonical pipe. The doctrine works -- it just wasn't enforced on the wholesale_agent layer where today's send originated.

## D. DNC list files (state-of-truth drift)

| File | Has Streubel? |
|------|--------------|
| `compliance/dnc_list.json` | YES (since 2026-05-05) |
| `wholesale_agent/opted_out_emails.json` | YES (since 2026-05-05) |
| `wholesale_agent/bounced_emails.json` | Separate concept (bounces), but `rex_stop_handler.is_suppressed()` only reads bounces + a local cache, NOT `opted_out_emails.json` -- so it failed to block. |
| `recipient_classifier.py` | YES, `municipalfirm` hardcoded -- but rex_belfort never calls the classifier. |

## E. `branded_mailer.py` itself -- the choke point -- has NO DNC gate

Confirmed by grep: zero references to `eradication`, `dnc`, `suppression`, or `opted_out` inside `branded_mailer.py`. So even if every bypass script migrated, the brand pipe still wouldn't have blocked Streubel. **This is the most important finding.** The brand pipe needs the gate.

## F. `.env` halt was dropped

`.env.bak` has `WHOLESALE_OUTBOUND_HALT=1` (set 2026-05-05). Active `.env` did NOT until this session (just restored). **Cause:** unknown -- possibly a deploy that overwrote `.env` from a template that didn't include the halt. **Fix:** restored + an explicit comment block documenting the lift criteria.

---

## How it happened, in chronological order

| When | What |
|------|------|
| 2026-04-24 | First outreach to Streubel from `piper@everlightventures.io` via Piper template (full branded). |
| 2026-04-26 | Second outreach went anyway. Streubel threatened BBB. Operator command: "stop, eradicate." |
| 2026-05-04..05 | DNC doctrine written. 3 storage locations updated. `.env.bak` got the halt flag. |
| (Unknown) | Active `.env` lost the halt flag. .env.bak retained it. Possibly during a sync or deploy. |
| 2026-05-14 cron tick | `rex_belfort_sequence.py` Day-2 follow-up fired for lead `leg_afee1a472d`. Called `rex_stop_handler.is_suppressed()` which checks bounces but NOT `opted_out_emails.json`. Result: not suppressed. Hit `api[.]resend[.]com` directly. No template applied. Subject: "Re: 4435 WESTMINSTER PL, SAINT LOUIS, MO 63108". |
| 2026-05-15 04:07 PT | Streubel replied: "wtf - No thanks. No need to contact me again." |

---

## What's locked NOW (this session, shipped)

1. **`WHOLESALE_OUTBOUND_HALT=1`** + **`ERADICATION_GATE_REQUIRED=1`** added to active `.env` with documented lift criteria.
2. **`03_AUTOMATION_CORE/01_Scripts/content_tools/eradication_gate.py`** created. Hardcoded Python module. 7/7 self-test cases PASS. Catches Streubel via email, email caps, domain, name substring, address substring, and lead_id. Independent of any JSON file.
3. **Memory entry** `feedback_streubel_permanent_eradication.md` written to `/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory/`. Every future Claude session will read this BEFORE acting on outbound.
4. **Audit log** at `Wholesale/compliance/eradication_gate_audit.log` -- every gate call (pass or fail) is appended JSON.

## What ships NEXT (this session, before commit)

5. **Patch `branded_mailer.send_branded_email()`** to call `eradication_gate.assert_safe()` BEFORE any Resend call. Makes the brand pipe also the DNC pipe. **This is the highest-leverage single change.**
6. **Patch the 13 bypass scripts in `wholesale_agent/`** to import and call `eradication_gate.assert_safe()` at the top of every send function. Even though doctrine says "migrate to branded_mailer," the immediate patch is gate-import so they fail closed.
7. **Renaming `rex_belfort_sequence.py` and `rex_7touch_sequence.py`** with a top-level `WHOLESALE_OUTBOUND_HALT` check that exits before any send loop runs. (Belt and suspenders.)
8. **Side-branch push** of all changes to `streubel-eradication-2026-05-15`, then main, so Oracle + PC both pick up the lockdown on next sync.

## Lift criteria (what has to be true before halt comes off)

- [ ] All 18 bypass scripts call `eradication_gate.assert_safe()` OR delegate to `branded_mailer`.
- [ ] `branded_mailer.send_branded_email()` gates by `eradication_gate.assert_safe()` unconditionally.
- [ ] Self-test runs on phone + Oracle + PC, 7/7 PASS on each.
- [ ] `rex_stop_handler.is_suppressed()` reads `opted_out_emails.json` AND `dnc_list.json`, not just bounces.
- [ ] Pre-commit hook `lint_no_direct_resend.sh` is wired and rejects new direct-Resend code at commit.
- [ ] Rich explicit greenlight on every line item above.

## Why this is now in memory (and not just in protocol files)

Three operator commands across three sessions said "do not contact Streubel." Each session honored it in the moment by writing to JSON files. Then a fourth session wrote a code path that didn't read those JSONs. **The fix is not another JSON file. The fix is a memory entry that loads into every future agent's context, plus a Python module hardcoded into source.** Now the "do not contact" rule lives in three places that survive sync, deploy, or file overwrite: memory (claude brain), source code (`eradication_gate.py`), and protocol files (existing JSONs). Triple redundancy.

---

## Embarrassment owned

- 2nd-strike send happened. Documented.
- Brand template skipped. Documented.
- Three prior commands ignored by automation. Documented.
- The pattern is now memory-resident. No 3rd strike.
