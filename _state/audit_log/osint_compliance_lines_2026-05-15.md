# OSINT Compliance Lines -- Pre-Build Legal Memo

**Author:** Priya Bhattacharya, Privacy & Data Counsel
**Date:** 2026-05-15
**Audience:** Rich (CEO), Justine Park (Compliance), engineering team building OSINT v2
**Classification:** Binding. Build to this. Deviations escalate to Theo Briggs.

I count 11 consent-failure modes in what Rich proposed. Three are hard "no." Four are conditional. Four are green. Here's the record.

---

## 1. License Plate Lookups -- HARD NO

**Statute:** Driver's Privacy Protection Act, 18 USC 2721-2725. Federal preemption floor; states layer on top (CA Veh Code 1808.21+, FL Stat 119.0712, TX Transp Code 730).

**Verdict: We do not run plates. Period.**

The 14 permissible purposes under 2721(b) are: (1) government agency function; (2) motor vehicle safety/theft/emissions; (3) legitimate business verifying info submitted by the individual; (4) court proceeding; (5) research with no contact; (6) insurance claims/underwriting; (7) notice of towed/impounded vehicle; (8) licensed private investigator for a permissible purpose; (9) employer commercial driver verification; (10) private toll service; (11) consent of the individual; (12) bulk marketing **only with express opt-in**; (13) state-authorized; (14) other use specifically authorized by state with consent.

None fit wholesale real estate prospecting. Purpose (3) requires the individual already submitted info to us -- a property owner pulled from assessor records did not. Purpose (12) requires express opt-in we do not have. Purpose (8) PI carve-out still requires the PI have a downstream permissible purpose; we do not.

Civil penalty under 2724: actual damages, $2,500 minimum per violation, punitive damages, attorneys' fees. Criminal under 2723: fines up to $5,000 per violation. There is a private right of action. Class actions exist.

**Free alternative we CAN do:** none on plates. Vehicle ownership is not a "not creepy" signal anyway -- if we knew it, we couldn't say it. Drop the entire lane.

---

## 2. Criminal Background -- SPLIT VERDICT

**Statutes:** Fair Credit Reporting Act, 15 USC 1681 et seq.; state mini-FCRAs (CA ICRAA Civ Code 1786, NY GBL 380, TX Bus & Com 20). Gramm-Leach-Bliley, 15 USC 6801, applies if we touch financial info.

**Seller side (property owner outreach): NO.**
Pulling a criminal record to decide whether to send marketing email is an "adverse action" trigger under FCRA if sourced from a Consumer Reporting Agency (TruthFinder, BeenVerified, Spokeo's paid tier, Intelius are all CRAs under 1681a(f) when used for eligibility decisions). Even if we self-justify "research only," the moment that record influences whether to send / what to offer, it's a permissible-purpose violation under 1681b. We have no FCRA-permissible purpose for sellers. $1,000 statutory + actual damages per violation.

**Buyer side (Open Deal Inner Circle vetting): CONDITIONAL YES.**
Inner Circle vetting *is* an eligibility decision (we let them into a paid tier; we hold their EMD). That gives us a FCRA-permissible purpose under 1681b(a)(3)(F)(ii) -- "legitimate business need in connection with a business transaction initiated by the consumer." Conditions:
- Use a credentialed CRA (we are already running Stripe Identity + OFAC -- extend that, do not bolt on a side aggregator).
- Written disclosure + signed consent **before** the pull. Stripe Identity flow already captures this; add the criminal-check checkbox.
- Adverse action notice if we deny: name of CRA, copy of report, right to dispute, FCRA summary of rights.
- 7-year lookback cap for non-convictions (1681c(a)); some states (CA, NY, MA) cap convictions at 7 years too.

**Public court record direct search vs aggregator:** Critical distinction. Direct search of Shelby County Criminal Court Clerk, PACER, state court portals = NOT a CRA pull, NOT FCRA-covered. But: if we use that data for an eligibility decision, some state mini-FCRAs (CA ICRAA) still apply because they regulate the USE, not just the source. Safer rule: any criminal data used for any Inner Circle decision goes through the CRA path with consent. Direct-search is for litigation prep only, not vetting.

**GLBA:** triggers if we cross-reference financial records (bank account, mortgage data). Stay clear of bank/credit data on the seller side entirely. Buyer side: Stripe handles the GLBA-covered piece; we never store it.

---

## 3. Social Media Username Sweep -- CONDITIONAL YES, NARROW

**Statutes:** Computer Fraud and Abuse Act, 18 USC 1030; Electronic Communications Privacy Act, 18 USC 2510-2523; platform Terms of Service (contract).

**Verdict: Public-profile-only is green. Anything requiring auth is no.**

Safe (build it):
- Sherlock / Holehe / EmailRep checking **public-by-default** profile existence across platforms. No login. No scraping behind auth. No password-spray. The username "rich_gee_memphis" returning hits on 8 platforms is public-record-equivalent under hiQ v. LinkedIn (9th Cir. 2022) -- scraping publicly accessible data is not CFAA "exceeding authorized access."
- Capture only: handle exists / handle does not exist. Do not download post content at scale.

Not safe (do not build):
- Logging into any platform with a sock account to view "friends only" content -- ToS violation, possible CFAA exposure post-Van Buren (2021).
- Email-to-phone or phone-to-account-discovery via leaked-credential databases. Even if technically public (HaveIBeenPwned API), using breach data for marketing enrichment is the textbook FTC unfairness case.
- Storing scraped post content. Capture signal, discard payload.

ECPA risk begins at intercepting communications in transit or accessing stored electronic communications without authorization (2701). Public profile reads do not trigger this. DMs, private posts, anything requiring credentials does.

---

## 4. Macro Signals -- ALL GREEN, ONE CAVEAT

- **NOAA weather** (api.weather.gov): green. Public domain federal data, no rate limit on reasonable use, no ToS issues. Cite "data: NOAA NWS."
- **USGS earthquakes** (earthquake.usgs.gov/fdsnws): green. Public domain, REST API, no auth required.
- **FHWA infrastructure** (geo.dot.gov, NBI): green. Federal open data.
- **Google News RSS:** yellow. The RSS feed is publicly served, but Google's ToS prohibits "scraping at scale" and there is no documented rate limit. Use it for ad-hoc lookups (one parcel, one query). If we want systematic news enrichment, use a real news API: NewsAPI.org (free tier 100/day), GDELT Project (free, federally funded, no ToS issue), or Bing News Search API. Prefer GDELT.

All four signals are background context, never quoted directly. We do not say "we saw the tornado warning"; we say "for owners in flood-prone Shelby zones we're flexible on close timing."

---

## 5. The "Not Creepy" Line -- 5 Examples

Even when 100% legal, output must be invisible-signal / relevant-result. Test: would the recipient feel surveilled if they reverse-engineered our process?

| Legal but CREEPY (banned) | Legal and PROFESSIONAL (ship) |
|---|---|
| "We noticed you inherited this property in 2019 from a probate filing." | "We work often with owners who inherited property and want a clean exit." |
| "Saw on Facebook you moved to Dallas -- want to sell your Memphis place?" | "We work with out-of-state owners like yourself." |
| "Public records show your taxes are 2 years behind." | "We can close fast and cover back taxes at the table." |
| "Your LinkedIn says you're an executive at FedEx -- you don't need this hassle." | "For owners with demanding careers we handle the entire process." |
| "Your divorce decree filed last March suggests you may want to liquidate." | "For owners going through transitions, we offer flexible timing." |

Rule for engineering: the OSINT signal informs the **segmentation**, never the **language**. If the only way to write the sentence requires naming the source, the sentence does not ship.

---

## 6. Per-State Matrix -- Active OSINT/Privacy Statutes

| State | Statute | Bite on us |
|---|---|---|
| **TN** | TN Consumer Protection Act, TCA 47-18-101; no comprehensive privacy law yet | Low. SB 909 disclosure already in PSA. |
| **TX** | TX Data Privacy & Security Act (TDPSA), Bus & Com 541 (effective 2024-07); SB 140 telemarketing | **Active.** TDPSA grants opt-out from targeted ads + sale of personal data. Add opt-out link to email footer in TX cell. |
| **FL** | FL Digital Bill of Rights, FS 501.701+ (effective 2024-07, $25M revenue threshold -- we likely below); FTSA FS 501.059 | FDBR likely does not bite (threshold). FTSA bites SMS -- we are email-only so safe, but Mona reviews every FL send. |
| **GA** | No comprehensive privacy law; GA Fair Business Practices Act, OCGA 10-1-390 | Low. Standard CAN-SPAM compliance. |
| **OH** | No comprehensive privacy law; pending Ohio Personal Privacy Act | Low for now. Monitor 2026 session. |
| **AZ** | AZ Consumer Fraud Act, ARS 44-1521; AZ DNC ARS 44-1278 | Lupe reviews every AZ send. No comprehensive privacy law yet. |
| **MO** | No comprehensive privacy law; MO Merchandising Practices Act, RSMo 407.020 | Low. |
| **NV** | NV Privacy of Information Collected on the Internet, NRS 603A.300+ (amended 2021); strict on sale of personal data | **Active.** Must honor opt-out of "sale" -- we do not sell data, but log the determination. |

Triggered comprehensive privacy laws: **TX (TDPSA), NV (NRS 603A)**. FL FDBR likely below threshold but we add the footer anyway. Engineering: add per-state opt-out link rendering to `branded_mailer.send_branded_email()`.

---

## 7. compliance_log.py -- Required Event Additions

The classifier is the gate; the log is the record. Add these events:

1. `osint_query_run` -- module, target identifier (hashed), purpose code, operator agent, timestamp.
2. `osint_source_classification` -- public_record / public_profile / CRA / aggregator / restricted. Restricted = halt.
3. `dppa_block_triggered` -- any attempted plate lookup. Hard-stop event for the audit trail (proves we declined).
4. `fcra_permissible_purpose_recorded` -- buyer-vetting only; cites 1681b subsection + consent capture ID.
5. `adverse_action_notice_sent` -- buyer-side only; CRA name, report copy reference, timestamp.
6. `state_privacy_law_applied` -- which state law gated the output (TDPSA, NRS 603A, etc.).
7. `creepy_filter_triggered` -- any pitch_tailor output that named a specific OSINT source got rewritten or blocked. Stores both versions.
8. `tos_check_passed` -- for each external API call: source, ToS version date, rate-limit posture.
9. `consent_record_pull` -- four-tuple (consent string, timestamp, channel, recipient class) for every send.
10. `gdpr_ccpa_dsar_received` + `dsar_fulfilled` -- 45-day clock under CCPA, 30-day under most state laws.

Hash-chain these the same way `deal_execution_log.py` does. Append-only. Justine and I audit quarterly.

---

**Bottom line, three sentences.** Plates are dead -- DPPA forecloses every purpose we have. Criminal background is split: no on sellers, yes on Inner Circle buyers through Stripe + adverse-action discipline. Social/macro signals are mostly green if we stay public-profile-only and never quote the source in outreach. Build to this.

Documented. Theo copied. Mona and Lupe looped on state cells. Mani holds the litigation contingency.

-- Priya
