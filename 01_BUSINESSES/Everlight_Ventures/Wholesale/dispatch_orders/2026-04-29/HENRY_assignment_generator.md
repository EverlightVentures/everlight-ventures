# Dispatch Order -- Henry "Hammer" Knox

**From:** Marcus Cole, Chief Operator
**Issued:** 2026-04-29 evening, autonomous-pipeline handoff
**Priority:** HIGH (gates phase 10 buyer assignment when first PSA signs)
**Boundary:** code build only. No outbound to humans. PDF generation locally. No e-sign send.

---

## Mission

Build `gen_assignment_agreement.py` per the spec at:

`/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/process_control/07_CHRIS_LOCK_STRUCTURE.md`

Layer 2 -- the Assignment Agreement that binds Chris (or any buyer) so they cannot circumvent us. Three required clauses:

- **Clause 2.1** -- Assignment Fee + GFAD payment trigger
- **Clause 2.4** -- GFAD refund conditions (the only outs: title unmarketable, seller default, force majeure)
- **Clause 2.6** -- Anti-circumvention (24-month, 2x liquidated damages + injunctive + attorneys' fees)

The clause text is verbatim in `07_CHRIS_LOCK_STRUCTURE.md`. Use it.

---

## Path

`/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/gen_assignment_agreement.py`

Mirror the structure of `gen_psa.py` -- read prefill JSON, take a parcel id, render PDF.

Parameters per call:
- parcel_id (required)
- buyer_name (default: "Mid South Homebuyers, LLC")
- buyer_address (loaded from `Wholesale/buyers/{slug}/buyer_profile.json`)
- assignment_fee_usd (loaded from psa_prefill `suggested_assignment_fee_usd`)
- gfad_usd (default $1,000; min $500, max $1,500)
- effective_date (default: today)

Output: `Broker_OS/wholesale_agent/contracts/assignment_{parcel}_{date}.pdf`

PDF template structure:
1. Title block + parties (Assignor = Everlight Ventures, Assignee = buyer entity)
2. Recital (references the underlying PSA by date + property)
3. Clause 2.1 -- Assignment Fee + GFAD trigger (verbatim from spec)
4. Clause 2.4 -- GFAD refund conditions (verbatim)
5. Clause 2.6 -- Anti-circumvention (verbatim)
6. Signature blocks (Assignor signature + date; Assignee signature + date)
7. Notary block optional (state-dependent; include for TN by default)

Use the same PDF generation library as `contract_generator.py` -- look at how `generate_wholesale_contract()` builds its PDF and mirror.

---

## Required code patterns

- Idempotent: re-run with same parcel_id should not double-write or change file.
- Validates that the underlying PSA exists at `Broker_OS/wholesale_agent/contracts/psa_{parcel}_*.pdf` BEFORE generating the assignment (you can't assign a contract that doesn't exist).
- Writes a sidecar JSON artifact: `seller_intel/{slug}/assignment_generated.json` with `{pdf_path, generated_at, parcel, buyer, fee, gfad}` -- the orchestrator reads this to advance phase 10.
- Logs the run via `content_tools.hive_logger.start("henry_knox", "gen-assignment-agreement", inputs=...)`.
- Refuses to generate if buyer slug not present in `Wholesale/buyers/`. Hard fail with a useful error.

---

## Test before shipping

Run `python3 gen_assignment_agreement.py "035093  00032"` (Mikal Hakeem parcel -- has psa_prefill data). Confirm:
- PDF generates without errors
- Clauses 2.1, 2.4, 2.6 are present and verbatim with the spec
- Signature blocks render cleanly
- Sidecar JSON written

If buyer profile JSON for chris_midsouth doesn't exist yet, create the stub at `Wholesale/buyers/chris_midsouth/buyer_profile.json` with the data from Chris's reply. That's a 5-min side build -- worth doing now since every assignment will need it.

---

## Boundary

You DO NOT:
- Send the PDF anywhere
- Auto-trigger Documenso e-sign
- Email Chris or any buyer
- Modify or auto-fire any other contract template (Penny owns deal package; Justine owns compliance)

You DO:
- Build the generator
- Test it on the Mikal parcel
- Stub the chris_midsouth buyer profile
- Slack ping `#war-room`: "Henry: gen_assignment_agreement.py shipped + tested on Mikal parcel. PDF at {path}. Ready for first signed PSA."

---

## Done criteria

- `gen_assignment_agreement.py` exists, runs, generates a clean PDF
- Sidecar artifact pattern written
- Hive logger integration present
- Test PDF reviewed (visually -- a human eye -- before claiming done)
- Slack ping fired

ETA: 30 minutes per spec. If you're past 60 minutes without ship, ping me with the blocker.

-- Marcus
