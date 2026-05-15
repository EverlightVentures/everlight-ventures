# Legal Patches -- Open Deal -- 2026-05-15

Synthesized from 5 legal audits (Theo Briggs, Heck Aurelio, Imani Calder, Priya Bhattacharya, Lo Hines TN). All five returned FIX REQUIRED, no BLOCKER. This file is the consolidated patch list.

---

## POST-DEAL-1 UNLOCKS (NOT pre-build blockers per Rich's macro/micro doctrine 2026-05-15)

These do NOT gate Deal 1 closing. They do NOT gate Browser tier shipping. They gate Verified + Inner Circle tier public launch. Each is funded by the Deal-1 commission.

### Unlock 1: Form Everlight Ventures Wholesale Acquisitions, LLC (NV parent + state subs)

- **Source:** Imani Calder, Patch 1 (structural)
- **Corrected entity name per Rich 2026-05-15:** "Everlight Ventures Wholesale Acquisitions, LLC" with state-specific subs (Memphis TN, Atlanta GA, DFW TX, etc.) NOT "Everlight Memphis Acquisitions." Empire-structured for multi-state.
- **Why:** until LLC exists, every Verified-tier charge and every Lock Fee forfeiture is personally indemnified by Rich as sole-prop, and Marquise is exposed as joint tortfeasor with no corporate veil. (Browser tier doesn't capture funds -- unaffected.)
- **Cost:** $300 TN SOS filing + $50/yr agent. NV parent +$425 + $200 annual list. Funded by Deal 1.
- **Time:** 72h once Rich greenlights
- **Owner:** legal_wen_marsh (corporate counsel)
- **Triggers:** before 2nd real Verified-tier capture. Browser tier ships without it.

### Unlock 2: Mid South Title Coordination Letter signature

- **Source:** Heck Aurelio, Patch 4
- **What it is:** one-page document signed by Everlight + Mid South confirming no kickback, no preferred pricing, no referral fee exchanged. RESPA Section 8 (12 USC 2607) paper trail.
- **Why:** without it, the Inner Circle Lock Fee credit + EMD-to-title structure has bare indirect-benefit exposure if a hostile regulator looks.
- **Cost:** $0. Relationship document.
- **Owner:** Marvin Cohen drives the conversation with Mid South; Heck drafts the letter.
- **Triggers:** before Inner Circle goes live (post-Deal-1, feature-flag gated).

### Unlock 3: Theo Briggs TREC public-platform memo

- **Source:** Lo Hines, finding 5
- **What it is:** written legal opinion that our principal-buyer-equitable-interest model under Tenn. Code Ann. 62-13-104(b) survives TREC scrutiny when the platform is publicly visible (drops, photos, asking prices).
- **Why:** TREC could argue the public `/drops` page is "soliciting prospective purchasers" under 62-13-102(4)(A). The principal-buyer exemption survives that argument; the memo is the written reasoning.
- **Cost:** $0 (in-house). Funded by Hive time only.
- **Owner:** legal_theo_briggs + Lo Hines TN-input
- **Triggers:** before Verified + IC tier goes public. Browser tier ships behind the signup-wall today.
- **Mitigation in build spec:** signup-wall + investor-acknowledgment checkbox makes Browser safe today. Verified + IC stay feature-flag gated until memo lands.

---

## PATCHES SHIPPED INLINE 2026-05-15

These are applied to the canonical spec files this session.

### Patch A: "Verified" -> "Buyer-Funds-Verified" (Theo Briggs Patch 1)
- Files: EMD_LOCK_POLICY.md, BUYER_DISCLOSURE_LOCK_FEE.md (next pass), OPEN_DEAL_BUILD_SPEC.md
- Hover tooltip: "Identity + funds confirmed. Not a representation of buyer creditworthiness, behavior, or fitness."
- DONE in EMD_LOCK_POLICY.md.

### Patch B: OFAC SDN screening required on Buyer-Funds-Verified + Inner Circle KYC (Theo Briggs Patch 2)
- File: EMD_LOCK_POLICY.md
- 5-minute manual check OR auto via Stripe Identity sanctions + Treasury SDN cron
- Logged with timestamp + version
- DONE.

### Patch C: CA geofenced OUT of paid tiers (Theo Briggs Patch 6 + Heck Aurelio escalation)
- Files: EMD_LOCK_POLICY.md (DONE), OPEN_DEAL_BUILD_SPEC.md (pending)
- Pending Cal. Civ. Code 1671(b) liquidated-damages analysis
- 10%-in-24-hours may be unconscionable in CA

### Patch D: License-exemption citation fix (Lo Hines TN, finding 2)
- File: BUYER_DISCLOSURE_LOCK_FEE.md
- Current: cites Tenn. Code Ann. 66-32-101 (SB 909, seller-facing)
- Correct: Tenn. Code Ann. 62-13-104(b) (principal-party exemption)
- Replace exact text in disclosure section 0 wholesaler license status.

### Patch E: Strike 1-year contractual SOL (Lo Hines TN, finding 4)
- File: BUYER_DISCLOSURE_LOCK_FEE.md
- Current: "any claim relating to this Lock Fee must be brought within one (1) year of the date of charge"
- Replacement: "any claim shall be governed by Tennessee statutory limitations periods"

### Patch F: SB 909 cross-reference (Lo Hines TN, finding 1)
- File: BUYER_DISCLOSURE_LOCK_FEE.md, section 2
- Add: "Seller of the property has been provided the separate disclosure required by Tenn. Code Ann. 66-32-101 (TN SB 909) prior to or contemporaneously with the wholesaler's purchase contract with seller."

### Patch G: 10% house fee consideration language alignment (Lo Hines TN, finding 3)
- Files: EMD_LOCK_POLICY.md, BUYER_DISCLOSURE_LOCK_FEE.md, Stripe descriptor
- Standard phrasing everywhere: "service charge for the 24-hour exclusivity window"
- DONE in EMD_LOCK_POLICY.md (consistent across tier table + PSA Schedule A clauses).

### Patch H: SMS to Chris OFF, Slack DM only (Priya Bhattacharya, finding 1)
- File: EMD_LOCK_POLICY.md "Chris Ulander handling" section
- Current: "Chris gets Slack DM + SMS the moment a drop is created"
- Replacement: "Chris gets Slack DM only. SMS rail OFF until both: (a) PEWC record on file per FCC 23-107, AND (b) Deal 3 closes (TN state_gates SMS gate)."

### Patch I: EU/UK/EEA geofence at CF Worker edge, return 451 (Priya Bhattacharya, finding 3)
- File: OPEN_DEAL_BUILD_SPEC.md
- Add to CF Worker spec: "Block requests from EU/UK/EEA IP ranges with HTTP 451 Unavailable for Legal Reasons. Use CF Workers `request.cf.country` field."

### Patch J: CAN-SPAM footer on drop emails (Priya Bhattacharya, finding 4)
- File: branded_mailer template + OPEN_DEAL_BUILD_SPEC.md
- Required: postal mailing address, opt-out link (Resend handles), "you opted in on [date]" line
- Drops are commercial under 16 CFR 316.3 primary-purpose rule, not transactional

### Patch K: Privacy policy publication at /legal/privacy (Priya Bhattacharya, finding 2)
- File: PRIVACY_POLICY.md (new, drafted next pass)
- $2,500-$7,500 per intentional CCPA violation per record. Day-1 ship is mandatory.

### Patch L: Granular pulse-feed consent + Chris ANCHOR badge consent (Priya Bhattacharya, finding 6)
- File: BUYER_DISCLOSURE_LOCK_FEE.md
- Add: opt-in checkbox at signup "I consent to my username (or chosen handle) and lock activity appearing in the public pulse feed."
- Chris ANCHOR badge: separate written consent (e-signed) before the gold crown ships in UI.

### Patch M: Signup-wall + investor-acknowledgment checkbox before property visibility (Lo Hines TN, finding 5)
- File: OPEN_DEAL_BUILD_SPEC.md
- Required: no property data visible without account. Account creation requires checkbox: "I am a real estate investor seeking to acquire investment properties. I am not a consumer purchasing a primary residence. I understand Everlight Ventures is the principal-buyer-equitable-interest holder under Tenn. Code Ann. 62-13-104(b), not a licensed real estate broker."
- Mitigates TREC public-platform argument; Browser tier can ship under this pattern.

### Patch N: Stripe processing fees absorbed on refunds (Imani Calder Patch 2)
- File: EMD_LOCK_POLICY.md + BUYER_DISCLOSURE_LOCK_FEE.md
- Current: "Stripe's payment-processing fee (~2.9% + $0.30) is non-refundable in all cases"
- Replacement: "Everlight Ventures absorbs the Stripe processing fee on any refund. Buyer receives the full 90% refund without further deduction."
- Cost: ~$222/mo at projected volume. Per Imani: "cheapest class-action insurance we'll ever buy."

### Patch O: KYC retention runbook (Priya Bhattacharya, finding 7)
- File: new `KYC_RETENTION_RUNBOOK.md` (Justine + Priya draft)
- 3 years from last activity; 1-year hard cap on government-ID images per TX CUBI
- Auto-purge cron on Oracle

### Patch P: Cross-channel STOP revocation (Priya Bhattacharya, finding 8)
- File: dnc_writeback.py + branded_mailer + branded_sms
- STOP on SMS revokes email too, per FCC 24-24 (April 2025)
- Mirrors David Streubel doctrine

---

## What gets shipped this session

- Patch A (Verified rename): EMD_LOCK_POLICY.md -- DONE
- Patch B (OFAC): EMD_LOCK_POLICY.md -- DONE
- Patch C (CA geofence): EMD_LOCK_POLICY.md -- DONE
- Patch D (cite fix): BUYER_DISCLOSURE_LOCK_FEE.md -- DOING NEXT
- Patch E (strike SOL): BUYER_DISCLOSURE_LOCK_FEE.md -- DOING NEXT
- Patch F (SB 909 ref): BUYER_DISCLOSURE_LOCK_FEE.md -- DOING NEXT
- Patch G (10% consideration phrasing): EMD_LOCK_POLICY.md -- DONE
- Patch H (Chris SMS off): EMD_LOCK_POLICY.md -- DOING NEXT
- Patch I (EU 451 geofence): OPEN_DEAL_BUILD_SPEC.md -- DOING NEXT
- Patch J (CAN-SPAM footer): OPEN_DEAL_BUILD_SPEC.md -- DOING NEXT
- Patch M (signup-wall): OPEN_DEAL_BUILD_SPEC.md -- DOING NEXT
- Patch N (absorb refund fees): EMD_LOCK_POLICY.md + BUYER_DISCLOSURE_LOCK_FEE.md -- DOING NEXT

## What gets deferred to the build sprint

- Patch K (privacy policy) -- PRIVACY_POLICY.md to draft separately
- Patch L (pulse-feed consent) -- engineering ticket in build spec
- Patch O (retention runbook) -- engineering ticket
- Patch P (cross-channel STOP) -- engineering ticket

---

## Open escalations to legal

- **Heck Aurelio** drafts Title Services Coordination Letter for Mid South -- Marvin drives signature
- **Theo Briggs** writes TREC public-platform memo -- blocks Verified + IC launch
- **Imani Calder** drafts Shelby County small-claims response templates (2 predictable scenarios) -- $0 defense cost when prepared
- **Justine Park + Priya Bhattacharya** draft KYC retention runbook
- **All five** queued for the 2L/3L sync per Theo Briggs note tomorrow at noon PT
