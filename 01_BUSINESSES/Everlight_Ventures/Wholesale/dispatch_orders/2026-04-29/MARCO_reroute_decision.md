# Marco Williams Re-Route Decision

**From:** Marcus Cole, Chief Operator
**Issued:** 2026-04-29 evening
**Trigger:** Marquise scrapped hand-delivery: "no one is hand-delivering anything"

---

## Decision

Marco Williams (1250 Dunnavant, mailing 1241 Dunnavant -- across the street) drops from same-day immediate-action. Re-route in this order:

1. **Email pattern guess + MX verify** -- 15-min Cipher task. Address is Memphis-local so any business he runs (LinkedIn / FB) may surface a domain. If MX-verified email lands, Marco moves to Tier-1 email queue tomorrow morning.

2. **Direct mail piece via Lob (when budget approves)** -- the 1241 Dunnavant mailing is verified; a Lob letter costs ~$1.50. Mail-only path lands him at Tier-2 (slower funnel) but still in the funnel.

3. **Door-knock by a contracted agent in Memphis** (NOT Marquise, NOT now) -- this is the original intent that made Marco the highest-priority physical-presence target in the batch. Park it for post-Deal-1 when we hire a Memphis VA / contracted door-knocker (per `VA_HIRING_KIT.md`).

**Tier-2 means:** he stays in `seller_intel/`, his intel.json + skip_trace artifacts persist, the orchestrator routes him to mail-only. He does NOT consume a slot in the 25/day email cap.

---

## Cipher's email-find task for Marco

Add to Cipher's dispatch list (`CIPHER_intel_deepdive.md`):

7. `026056__00056` -- **Marco Williams** -- 1250 Dunnavant -- mailing 1241 Dunnavant Memphis TN 38106
   - Need: any business email tied to him
   - Path 1: WebSearch "Marco Williams" + "1241 Dunnavant" or "Memphis 38106"
   - Path 2: TN Sec of State LLC search "Marco Williams" Memphis -- if he runs an LLC, registered agent record surfaces email
   - Path 3: LinkedIn public profile "Marco Williams Memphis"
   - Path 4: FB business page lookup (he owns property next to a rental; might be a small landlord operation)
   - If nothing surfaces: write skip_trace.json with `email: null` + `mail_path: "1241 Dunnavant St, Memphis, TN 38106"` + `notes: "tier-2 mail-only; door-knock deferred per Marquise"`. Mark `confidence: 0.65` (matches Phil's existing rating) -- name is real, address is real, person is real.

---

## What this changes in the pipeline

- 14 priority leads -> 14 priority leads (Marco does not drop from the list, only from the immediate-action queue)
- Same-day actions: 2 emails ready to fire (Mikal + Trezden) + 7 Cipher email-finds (6 originals + Marco)
- Hand-delivery action item: REMOVED. Re-routed.

The file `seller_intel/SELLER_EMAILS_READY_TO_FIRE.md` line:
> "1 ready (door-knock) ........... Marco Williams (letter PDF generated)"

needs to update to:
> "1 ready (mail-only, tier-2) ........... Marco Williams (door-knock deferred to post-Deal-1 contracted agent)"

Charles flags this in the sunrise audit. I'll fix the file inline now.

-- Marcus
