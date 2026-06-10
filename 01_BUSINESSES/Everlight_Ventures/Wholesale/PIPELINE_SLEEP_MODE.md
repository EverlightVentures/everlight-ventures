# Wholesale Pipeline -- Sleep Mode (2026-04-29 evening)

**Watch officer:** Marcus Cole, Chief Operator
**State:** sleep-mode -- no auto-fire to humans until Marquise's morning review
**Wake time:** sunrise (06:00 PT) -- Charles Dawson runs the Operator Truth audit, posts to `#war-room`

---

## Boundary state (in force)

The Hive runs autonomously OVERNIGHT on these tasks ONLY:

| Task | Owner | Boundary |
|---|---|---|
| Intel deepdive on 6 priority leads + Marco | Cipher Wolfe | Public records / WebSearch / LinkedIn / MX dig only. No outbound. |
| Backfill 14 skip_trace.json artifacts | Phil Banks | Local file write only. No outbound. |
| Probe 4 NEEDS_MORE_INTEL leads | Phil Banks | Sec of State / IRS / USPS / public records only. No phone calls. |
| `gen_assignment_agreement.py` build + test | Henry Knox | Local code + test PDF. No e-sign send. |
| `gen_buyer_package.py` build + test | Penny Vance | Local code + test PDF. No buyer email. |
| Sunrise Operator Truth audit | Charles Dawson | Read-only. Posts honest report at 06:30 PT. |

The Hive does NOT run autonomously on these (Marquise approves):

- Outbound email to any seller (Mikal, Trezden -- ready and waiting)
- Outbound email to Chris (confirmation drafted at `buyers/CHRIS_CONFIRMATION_NOW.md`)
- Outbound to title firm (Mid-South Title intro call -- Marquise dials Tuesday)
- Wire instructions, GFAD requests, any money movement
- Documenso / e-sign send
- New state's compliance gates ON-switch
- New lead source ON-switch

---

## Where the dispatch orders live

`/Wholesale/dispatch_orders/2026-04-29/`
- `CIPHER_intel_deepdive.md`
- `PHIL_skiptrace_fallbacks.md`
- `HENRY_assignment_generator.md`
- `PENNY_buyer_package_template.md`
- `CHARLES_sunrise_audit.md`
- `MARCO_reroute_decision.md`

Each file: mission, paths, schema, boundary, done criteria. Single source of truth.

---

## Where Marquise picks up at sunrise

1. Read Charles's audit post in `#war-room` (~06:30 PT)
2. Approve the 2 ready emails (Mikal + Trezden) by reviewing them at `Wholesale/seller_intel/SELLER_EMAILS_READY_TO_FIRE.md`, then dropping the file `outreach_queue/pending_approval/{slug}_email_approved.json` to fire (or running the explicit fire command)
3. Send the Chris confirmation by reviewing `buyers/CHRIS_CONFIRMATION_NOW.md` and copy/pasting / firing
4. Decide whether to proceed with the 4 NEEDS_MORE_INTEL leads (Howard Eddie / Carnegie / Greater Love / Toby Jones) based on what Phil surfaced overnight
5. Tuesday: dial Mid-South Title using `process_control/06_MIDSOUTH_TITLE_INTRO_CALL.md`

---

## Single biggest morning risk

Phil's `REX_SKIP_TRACE_2026-04-29.md` is a markdown report -- the orchestrator's phase detector reads structured `skip_trace.json` artifacts. Until Phil's backfill lands, the orchestrator reports 14 leads as `skip_trace_pending` even though the data exists. Reality: 2 ready to fire, 12 mail-only. The orchestrator pulse will under-report progress until backfill runs.

If Phil's backfill is ready by Charles's 06:30 audit, this risk vanishes. If not, Charles flags it, and Marquise fires manually from the SELLER_EMAILS_READY_TO_FIRE doc.

---

## Orchestrator pulse from tonight

Snapshot: `/mnt/sdcard/AA_MY_DRIVE/_logs/wholesale_orchestrator/pulse_20260429T223916Z.json`

```
total: 32 leads
phase 3 (buybox_gate -> needs intel): 18
phase 4 (intel_deepdive -> needs skip_trace): 14
sends_today: 0
cap_remaining: 25/25
```

Recurring run: orchestrator can be cron'd on Oracle every 30 min (06:00-21:00 PT) once Oracle reachability returns. Until then, runs manually or per-deploy.

---

Sleep mode active. Watch is mine.

-- Marcus
