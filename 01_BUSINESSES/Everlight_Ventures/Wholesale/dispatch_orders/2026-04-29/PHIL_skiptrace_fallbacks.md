# Dispatch Order -- Phil "Filter" Banks

**From:** Marcus Cole, Chief Operator
**Issued:** 2026-04-29 evening, autonomous-pipeline handoff
**Priority:** MEDIUM (gates 4 NEEDS_MORE_INTEL leads)
**Boundary:** terminal-side fallbacks ONLY. No outbound to humans. No paid services until Deal 1.

---

## Mission

Four leads are blocked at NEEDS_MORE_INTEL. Free-tier phone-side skip-trace returned 403 (Cloudflare anti-bot). Try terminal-side fallbacks now -- the avenues that don't require browser-rendered DOM.

Output format: `seller_intel/{slug}/skip_trace.json` (same schema as Cipher's order; see `CIPHER_intel_deepdive.md`).

---

## The 4 leads

1. `024057__00012` -- **Howard Eddie estate** -- 117 Farrow Ave -- mailing 1919 Jamar #230, San Antonio TX 78226
   - Need: heir / executor first name
   - Path 1: Shelby County Probate Court CSV / OData API if available (search "Eddie Howard" decedent, 2018-2024)
   - Path 2: Texas Bexar County (San Antonio) public voter registration -- name lookup at apartment 230
   - Path 3: USPS Address Lookup for any name on file at the unit
   - Path 4: Reverse-lookup the apartment address on Find-A-Grave for any HOWARD with a 78226 mailing
   - If still nothing: write artifact with `notes: "estate heir not surfaced; route to Shelby Probate browser MHTML when Oracle Playwright lands"` -- mark `mail_path: "Estate of Eddie Howard, c/o Apt 230 [no first name -- BLOCKED until probate]"` -- the lead stays in NEEDS_MORE_INTEL.

2. `034026__00014` -- **Carnegie Church of God in Christ** -- 1577 McMillan St -- mailing 5340 Santa Monica St (no city in DB)
   - Need: pastor or trustee first name + correct mailing zip
   - Path 1: TN Sec of State nonprofit registry -- search "Carnegie Church of God in Christ" -- registered agent name + officer roster is public
   - Path 2: TN Comptroller Charity Registry (`tnsos.org` charity search)
   - Path 3: COGIC Memphis Jurisdiction directory -- public website usually lists pastor name per congregation
   - Phone path: (901) 942-2500 is the published church business line. **Do NOT call it from this dispatch.** That's a Marquise-approval action. Leave it as a `next_action` field in the artifact.

3. `048003__00007` -- **Greater Love For Life Ministries Inc** -- 1537 Wilson St -- mailing PO Box, Albuquerque NM
   - Need: officer / registered-agent first name + EIN if active
   - Path 1: NM Sec of State business search -- nonprofits public, includes officers + registered agent
   - Path 2: IRS Pub 78 (charity lookup) -- if 501(c)(3) registered, address on file
   - Path 3: TN Sec of State -- if doing business in TN as a foreign entity, may have a TN registered agent

4. `034042__00014` -- **Toby Jones** -- 1596 Gabay St -- mailing "3772 Socorro" with NO city/state/zip
   - Need: resolve mailing zip first; THEN skip-trace the resolved address
   - Path 1: Re-pull assessor MHTML for parcel 034042 00014 (the original parse may have truncated the mailing line)
   - Path 2: USPS Address Lookup for "3772 Socorro" -- could be Socorro NM, Socorro TX, El Paso TX, or somewhere else
   - Path 3: If multiple matches, narrow by Memphis-tied owners (Shelby Register of Deeds name search "Toby Jones" -- if he owns other Memphis parcels, his mailing may resolve there)

---

## Also -- a backfill task

Your `REX_SKIP_TRACE_2026-04-29.md` is a great markdown report but the orchestrator needs structured artifacts. Please backfill `skip_trace.json` files for all 14 priority leads from your Apr 29 batch (the data is already in your markdown). One file per lead. This is a copy-paste job -- 15 minutes -- and unlocks the orchestrator's phase detection for everyone.

Schema (per `CIPHER_intel_deepdive.md`). Use your `Status` field to populate `email_mx_verified` (true if "READY_FOR_OUTREACH (email verified)", false otherwise). Use your `Confidence` for `confidence`.

---

## Boundary

You DO NOT:
- Subscribe to any paid skip-trace service
- Place any phone call
- Send any outbound email
- Run automated browser scrapes from phone-side (Cloudflare blocks; route through Oracle when reachable)

You DO:
- API + CSV + RSS where the source publishes it
- Sec of State + IRS + USPS public records
- Backfill the 14 skip_trace.json artifacts from your existing markdown
- Honest negative writes

---

## Done criteria

- 4 NEEDS_MORE_INTEL leads have a `skip_trace.json` artifact (verdict: surfaced or honest negative)
- 14 priority leads from Apr 29 batch have structured `skip_trace.json` files written
- Slack ping to `#war-room`: "Phil: backfilled 14 skip-traces; 4 NEEDS_MORE_INTEL probed -- {N} unblocked, {M} still blocked on {reason}"

-- Marcus
