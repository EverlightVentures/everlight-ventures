# Dispatch Order -- Penny Vance

**From:** Marcus Cole, Chief Operator
**Issued:** 2026-04-29 evening, autonomous-pipeline handoff
**Priority:** HIGH (gates phase 10 buyer-package send when first PSA signs)
**Boundary:** template + assembly logic only. No outbound to Chris or any buyer.

---

## Mission

Pre-stage the deal-package template that goes to Chris (or any buyer) when the first PSA signs. Today, that packaging is free-form -- a risk because it slows phase 10 and introduces inconsistency. The fix: a single command produces a Documenso-ready package, every time.

---

## What the package contains

Per `AUTONOMOUS_WORKFLOW_PATTERN.md` Phase 10:

1. PSA copy (signed by seller)
2. EMD wire confirmation (from Mid-South Title escrow)
3. Property photos (assessor public, plus any drive-by Marquise has)
4. Assessor data sheet (parsed JSON formatted as a 1-page summary)
5. TN SB 909 wholesaler disclosure (already executed at PSA stage)
6. Cover memo to buyer -- 1 page, written for executive scan

Add for the first deal with Chris specifically:
7. Brief one-paragraph note re: MAO formula confirmation (the strategic question deferred from the v3 reply)

---

## Path

`/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/gen_buyer_package.py`

Plus a template directory:
`/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/buyer_packages/templates/`
- `cover_memo_template.md` (Jinja-style {{ placeholders }})
- `assessor_summary_template.md` (1-pager from parsed JSON)

---

## Cover memo template

Draft the 1-page cover memo (Marquise reviews, then it's the canon). Tone: investor-to-investor, factual, brief. No marketing language.

Required sections:
1. **Property** -- 1 line: "{address}, {parcel}, {appraisal}, {build_year}, {type}"
2. **Seller status** -- 1 line: "PSA signed {date}, EMD ${amount} on deposit at Mid-South Title escrow"
3. **The package below contains** -- bulleted list of attachments
4. **Assignment terms** -- 2 lines: "Assignment fee: ${fee}. Good-faith assignment deposit: ${gfad} to title escrow within 48 hours of Assignment Agreement execution. Balance at closing."
5. **Title firm** -- 1 line: "Mid-South Title (Memphis), RESPA-compliant, escrow account confirmed"
6. **Close target** -- 1 line: "{date} -- 14 days from PSA execution"
7. **Next step** -- 1 line: "Reply with intent + we send the Assignment Agreement via Documenso"
8. Signature block: Marquise + Everlight Ventures contact

Cap at one printed page (200 words max).

---

## Generator behavior

`python3 gen_buyer_package.py "{parcel}" --buyer chris_midsouth`

1. Reads `seller_intel/{slug}/psa_signed.json` -- fails with clear error if missing
2. Reads `Wholesale/buyers/chris_midsouth/*.json` for buyer-specific fields
3. Reads `psa_prefill_{date}.json` for deal economics
4. Renders cover memo from template
5. Assembles package: PSA PDF + assessor sheet + photos + cover memo into ONE combined PDF (use pypdf2 or reportlab merge)
6. Writes sidecar `seller_intel/{slug}/buyer_package_drafted.json` with `{package_pdf_path, drafted_at, buyer_slug, parcel}`
7. Drops the package PDF into `Wholesale/buyer_packages/pending_approval/` (Marquise reviews, then a separate fire script sends -- you do NOT auto-send)
8. Slack ping `#war-room`: "Penny: deal package drafted for {parcel} ({buyer}). Awaiting Marquise approval."

---

## Boundary

You DO NOT:
- Email Chris or any buyer
- Trigger Documenso send
- Modify the PSA or Assignment Agreement (those are Henry's templates)
- Wire money or move escrow

You DO:
- Build the template + generator
- Render the first test package using Mikal's parcel + Chris's buyer profile
- Drop test package into `pending_approval/` for Marquise review
- Stub `Wholesale/buyers/chris_midsouth/buyer_profile.json` if not present (coordinate with Henry -- one of you stubs it; cross-check before duplicating)

---

## Done criteria

- `gen_buyer_package.py` exists, runs, produces clean combined PDF
- Cover memo template at `buyer_packages/templates/cover_memo_template.md`
- Test package generated for Mikal parcel + chris_midsouth buyer
- Test package PDF visually reviewed (eyeball -- not just file-exists)
- Slack ping fired

ETA: 45 minutes. The cover memo wording is the bottleneck -- get the template tight, the merge logic is straightforward.

---

## Why this matters

Phase 10 is where deals stall in wholesaling -- the buyer wants the package today, the wholesaler scrambles. This template + generator means: signed PSA in, package PDF out, in 30 seconds. That's the difference between a 36-hour buyer-response window we hit and one we miss.

-- Marcus
