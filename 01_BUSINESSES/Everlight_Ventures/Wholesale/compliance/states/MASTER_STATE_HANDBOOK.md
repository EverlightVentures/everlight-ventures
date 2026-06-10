# Master State Handbook — Real Estate Wholesaling

**Last Updated:** 2026-05-05 10:55 PT (2026-05-05T10:55:00-07:00)
**Purpose:** Operator-level reference for Marquise Smith / Everlight Ventures multi-state wholesaling. 30-year horizon. Read for understanding, not just compliance check-the-box.
**Audience:** Marquise (operator), Bernard Calloway (regulatory), Justine Park (compliance gate), Hammer Knox (closing), Hive agents.
**Status:** Framework v1.0. Per-state pages live alongside this index. Re-review every 18 months OR on any material statutory change.

---

## How to use this handbook

1. **Pick a state.** Read its full playbook page before any outreach in that market.
2. **Match the rules.** Cross-reference `state_gates.json` for the canonical operational config. The handbook explains the "why" behind each gate.
3. **Decide the volume.** Some states are unlimited-with-disclosure (TX, GA, FL, AZ, MO, OH). Some have informal volume thresholds before "engaged in business" triggers a license/bond requirement (TN at ~4 deals/year). Plan accordingly.
4. **Configure the channels.** Email + direct mail are universally compliant if the disclosure rides along. Cold SMS and cold voice are blocked or restricted in most states; default to email-first.
5. **Set the title routing.** Each state has a closing model (title-company state, attorney state, hybrid). Use the title partner already in `title_companies.json` for that market, or source a new one and add it.
6. **Generate the disclosure.** Each state has its own statutory disclosure form. The standalone DocuSign / Documenso envelope is the audit-defensible delivery mode.
7. **Track the deals.** Every closed deal increments the volume counter. When volume nears the state's threshold (TN especially), revisit the licensing decision.

---

## The 4-question state intake (run for every new state we want to add)

Before adding a new state to `state_gates.json`, answer these in writing:

1. **Is wholesaling legal without a real estate license?** If no, the state is BLOCKED unless we obtain the license (which we won't for occasional-volume markets).
2. **What disclosure must we deliver, to whom, when, on what surface?** No state has zero disclosure. The format varies (PSA paragraph, standalone notice, marketing footer).
3. **What channels are open?** Email is almost always open with disclosure + CAN-SPAM footer. SMS is restricted in most states. Voice is TCPA-exposed. Direct mail is open in all states with disclosure on the same physical sheet.
4. **What's the title-routing model?** Title-company state (TX, GA, FL, MO, OH, AZ, TN) — closing flows through a TX-licensed (or state-licensed) title agency. Attorney state (NC, SC, GA partial) — a licensed attorney conducts the closing. Hybrid — some counties title-company, others attorney.

If all four answers are clean, the state goes into `state_gates.json` as `active_in_pipeline: true`. If any one is restricted or unclear, the state stays parked.

---

## State catalog (priority order — see also `state_gates.json`)

### Active operating lanes (config + buyer + title verified)

- **[TN — Tennessee](TN_PLAYBOOK.md)** — Memphis pipeline live. Anchor buyer: Chris Ulander @ Mid South Homebuyers. Title: Mid-South Title (Memphis). Volume ceiling: ~4 deals/year without $50K surety bond.
- **[TX — Texas](TX_PLAYBOOK.md)** — DFW + Houston pipeline in build. Anchor buyer: pending Hammer cold-blast. Title: 1st Option Title (Garland) primary, Patten Title Houston secondary, Affinity Title DFW backup. No volume ceiling. SB 1577 §5.0205 disclosure mandatory pre-assignment.

### Configured but not yet activated (need anchor buyer + RESPA letter)

- **[GA — Georgia](GA_PLAYBOOK.md)** — Atlanta. Title partners in `title_companies.json`: Katz Durell LLC + Bagwell & Associates. Attorney-close state (different than TX).
- **[FL — Florida](FL_PLAYBOOK.md)** — Jacksonville + Tampa + Miami. Title partners: Marina Title + FL Title Closings.
- **[MO — Missouri](MO_PLAYBOOK.md)** — St. Louis + Kansas City. Title partners: Freedom Title + Investors Title Company.
- **[OH — Ohio](OH_PLAYBOOK.md)** — Cleveland + Columbus + Cincinnati. Title partners: Black Tie Title + Ohio Real Title Agency.
- **[AZ — Arizona](AZ_PLAYBOOK.md)** — Phoenix + Tucson. Title partners: TBD.

### Restricted / blocked (do not operate without further work)

- **NC — North Carolina** — HB 797 requires real estate brokerage license to wholesale repeatedly. BLOCKED in `state_gates.json`. Re-evaluate only if license is obtained.
- **CA — California** — pre-foreclosure outreach restricted by CA Civil Code §2945. Spanish-translation requirement under Civil Code 1632. Lapsed CA salesperson license held by Marquise creates additional disclosure complexity. PARTIALLY BLOCKED.
- **NY, NJ, MA** — restrictive multi-statute regimes, low ROI for wholesale. NOT EVALUATED.

---

## Universal operating rules (apply in every state)

These rules apply regardless of state-specific overlays:

1. **Owner identity:** outbound from `piper@`, `hammer@`, or `marcus@everlightventures.io`. NEVER from `rich@` or `1m.rich.gee@gmail.com`. Hard-rejected at code level by `resend_manager.py`.
2. **DTPA verb scrub:** no "I buy" / "we buy" / "we'll buy your house" copy. Replace with "we or an assignee will purchase." Send-time gate blocks any violation. Phrase deny-list at `pre_send_phrase_scrub.py`.
3. **CAN-SPAM:** every email has a physical postal address (Sacramento CA on file) + working unsubscribe in the footer.
4. **Engagement letter sign-gate:** no deal advances to `status='closing'` without `engagement_letter_signed_at` set. Helper: `rex_utils.mark_engagement_letter_signed(deal_id)`.
5. **DNC:** centralized at `content_tools/dnc_gate.py`. Reads + writes BOTH `wholesale_agent/opted_out_emails.json` (lite) and `compliance/dnc_list.json` (rich). Streubel and any other suppressed lead is hard-blocked at every send path.
6. **SMS / voice:** SMS is BLOCKED in TX (SB 140), TN (TSA 47-18-2002), and most other states without registration + bond. Cold voice is TCPA-exposed in every state without a national DNC scrub. **Default operating mode: email + direct mail only.** Voice and SMS lanes activated per state only after vendor signups.
7. **State disclosure:** every outbound to a state-domiciled lead carries that state's required disclosure footer (`state_advertising_disclaimers.py`). Every assignment-stage delivery carries the standalone state-specific disclosure envelope (Documenso).
8. **Compliance triple-check before any new state goes live:** Bernard regulatory red-team + Justine workflow gate + audit-doc binder. Pass = ship. Fail = remediate.

---

## How to add a new state to the operational pipeline

Step-by-step process (for Marquise + Bernard + Justine):

1. **Research:** dispatch a researcher agent with the 12-question state intake template. Outputs an `<XX>_PLAYBOOK.md` draft.
2. **Bernard countersign:** Bernard reads the draft, red-teams the legal claims, and either signs off or flags gaps. If flagged, return to research.
3. **External counsel review (optional but best-practice):** for high-volume states or states with criminal-misdemeanor penalty regimes (TX), engage state real estate counsel for a one-page sign-off. Until external review lands, the state ships under "internal posture."
4. **Justine workflow gate:** ensure `state_gates.json` config matches the playbook + the disclosure file exists at `compliance/states/<XX>_DISCLOSURE_v1.0.md` + the title partner is in `title_companies.json` with `respa_attestation_signed: true`.
5. **Title partner RESPA letter:** Hammer phone-verifies the title partner + sends the attestation request from `audit_kit/05_respa_title/RESPA_ATTESTATION_REQUEST_TEMPLATE.md`. Filed signed letter = green light.
6. **Anchor buyer signed:** Hammer cold-blasts target buyer list per market. Anchor signs (email handshake or written agreement) before any seller-side outreach goes live.
7. **First test deal:** drop a fixture inbound through `state_offer_workflow.py`. Verify the chain runs end-to-end (comps → ARV → MAO → offer → PSA → marcus_queue → manifest).
8. **Switch `active_in_pipeline: true`** in `state_gates.json`. State is now live.

Estimated time: 2-4 weeks per state, mostly waiting on Bernard, Hammer phone calls, and anchor buyer responses. Engineering work per state is hours, not days.

---

## How to read a state playbook page

Each `<XX>_PLAYBOOK.md` follows this structure:

1. **Quick verdict** — one-sentence legal status
2. **Wholesale licensing requirement** — license needed? threshold?
3. **Required wholesaler disclosure** — what / to whom / when / surface
4. **Volume thresholds** — when "occasional" becomes "engaged in business"
5. **Surety bond / fee** — if any
6. **Title closing model** — title-company / attorney / hybrid
7. **Channel restrictions** — SMS / voice / email / direct mail
8. **Option period / inspection period** — statutory or contractual, length
9. **Penalty regime** — criminal / civil / both
10. **Tax economics** — income tax, cap gains, transfer tax, recordation, treatment of wholesaling income
11. **Best wholesale-friendly metros** — top 1-3 markets
12. **Recent material change** — 2024-2026 statute / opinion / ruling
13. **Active configuration** — active_in_pipeline status + buy-box + title partner + anchor buyer
14. **Sources** — statute URLs + attorney commentary + dates
15. **Last counsel review** — Bernard + (external if signed)

---

## Re-review schedule

This handbook is reviewed:

- **Every 18 months** regardless of statutory activity (mandatory full pass)
- **Within 30 days** of any state legislature passing a new wholesaler-disclosure / licensing statute
- **Within 30 days** of any TREC / state real estate commission bulletin materially refining wholesaler obligations
- **Within 7 days** of any material change to a state we are actively operating in

Next mandatory review: **2027-11-05.**

---

## Companion documents

- `TAX_ECONOMICS_OVERLAY.md` — state-by-state tax rates, havens, credits, treatment of wholesaling income
- `STATE_COMPLIANCE_MATRIX.md` (existing) — operational matrix
- `state_gates.json` (existing) — canonical config file
- `title_companies.json` (existing) — title partner registry
- `state_advertising_disclaimers.py` (existing) — outbound footer text per state
- `DISCLOSURE_TEMPLATES.md` (existing) — pre-existing disclosure language drafts

---

**Owner:** Marquise Smith (final decision-maker)
**Editor:** Bernard Calloway (regulatory, web research lead)
**Compliance Gate:** Justine Park (workflow audit)
**Closing Operations:** Hammer Knox (title + buyer + RESPA letters)
