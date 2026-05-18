# Legal Disclaimer Audit -- OSINT Report Renderer

**Editor of record:** Bernard "Brief" Calloway, Bravo World Desk, Perplexity Intel
**File audited:** `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/osint_api/report_renderer.py` lines ~244-279
**Standard:** NY bar; Bluebook 21st ed.; current as of 2026-05-12
**Bottom line:** disclaimers are directionally correct but cite-thin. Six tightenings below.

---

## 1. FCRA citation -- ADD subsections

The top-level cite "15 U.S.C. § 1681 et seq." is correct as a **statute-name** reference, but a non-consumer-report disclaimer should pin the **operative subsections** so the reader sees exactly which uses are excluded.

**Add inline:** `15 U.S.C. § 1681a(d)` (consumer-report definition), `§ 1681b` (permissible purposes), `§ 1681m` (adverse-action notices). The point is to put the specific gating sections in front of the operator so a court or regulator sees the disclaimer was drafted with knowledge of the regulatory edges, not generically.

**Replacement sentence:**
> This report is NOT a "consumer report" as defined in 15 U.S.C. § 1681a(d) and may not be used for any "permissible purpose" enumerated in 15 U.S.C. § 1681b -- including credit, employment, insurance underwriting, tenant screening, or any decision triggering an adverse-action notice under 15 U.S.C. § 1681m.

## 2. GLBA scope -- TOO NARROW; cite the pretexting sections

"All financial information referenced is from publicly available sources" understates the obligation. GLBA's Title V (15 U.S.C. §§ 6801-6809) governs the safeguards rule; the **pretexting** prohibition lives in §§ 6821-6827. The current disclaimer disclaims pretexting in plain English but cites nothing.

**Replacement sentence:**
> No nonpublic personal information was obtained from any financial institution, nor was any such information solicited under false, fictitious, or fraudulent pretenses, in compliance with the Gramm-Leach-Bliley Act, 15 U.S.C. §§ 6801-6809 (privacy) and §§ 6821-6827 (pretexting prohibitions).

## 3. CCPA/CPRA -- ADD; California operators will consume this

California is in the operator footprint. Cal. Civ. Code § 1798.100 et seq. (CCPA, as amended by CPRA, Cal. Civ. Code § 1798.140) gives a California "consumer" the right to know, delete, and correct personal information collected about them, including by businesses meeting the § 1798.140(d) thresholds. Even if Everlight is below the threshold today, disclaiming forward is cheap.

**Add block:**
> **California Consumer Privacy Act / California Privacy Rights Act:** California residents have rights under Cal. Civ. Code § 1798.100 et seq. (as amended by Proposition 24, eff. Jan. 1, 2023) to request access to, correction of, or deletion of personal information collected about them. Direct requests to `privacy@everlightventures.io`. This report is generated for an internal "business purpose" within the meaning of Cal. Civ. Code § 1798.140(e) and is not sold or shared as defined in § 1798.140(ad)-(ah).

## 4. GDPR -- ADD a conditional one-liner; do not over-claim

US-focused but cheap to cover. GDPR Article 6(1)(f) (legitimate-interest) is the realistic basis for OSINT; Article 6(1)(a) (consent) does not apply to subjects unaware of the investigation.

**Add block:**
> **EU/UK General Data Protection Regulation:** Where any data subject is located in the EU or UK, processing is conducted under the legitimate-interest basis of GDPR Article 6(1)(f) (and UK GDPR equivalent), balanced against the data subject's rights under Articles 15-22. This report is not transferred outside the controller absent a valid Article 46 mechanism.

## 5. Defamation safe harbor -- STRENGTHEN

"Findings may be inaccurate, incomplete, or about a different person sharing the same name" is a good start but reads as a hedge, not a safe-harbor frame. The defensive posture is **opinion + qualified privilege + no republication**.

**Replacement sentence:**
> All findings are presented as preliminary investigative leads, not statements of fact, and are subject to verification. Identity-match errors (commonly known as "mixed files") are a known limitation of OSINT aggregation; recipients must independently confirm identity before relying on or republishing any finding. Republication outside Everlight Ventures' authorized personnel voids the qualified common-interest privilege under which this report is shared.

State-specific anti-defamation statutes (e.g., Cal. Civ. Code § 47(c) common-interest privilege; N.Y. Civ. Rights Law § 74) operate by common law in most jurisdictions; the "qualified common-interest privilege" phrase is the load-bearing language and travels.

## 6. INTERNAL USE ONLY -- ADD the Trade Secret hook

The current block is operationally clear but legally light. Add a Defend Trade Secrets Act of 2016 (18 U.S.C. § 1836) trade-secret designation -- it costs one sentence and gives Everlight standing if the report is leaked.

**Append:**
> This report and its compiled intelligence constitute a trade secret of Everlight Ventures within the meaning of 18 U.S.C. § 1839(3) and are protected under the Defend Trade Secrets Act, 18 U.S.C. § 1836.

---

## Filed
Bernard "Brief" Calloway -- Bravo World Desk
For routing to Justine Park (Claude Corp Compliance) for operational sign-off, and to Docket Wen for Bluebook second-pass on cite formatting.

Source?
- 15 U.S.C. §§ 1681, 1681a, 1681b, 1681m (FCRA)
- 15 U.S.C. §§ 6801-6809, 6821-6827 (GLBA)
- Cal. Civ. Code § 1798.100 et seq. (CCPA/CPRA)
- Cal. Civ. Code § 47(c); N.Y. Civ. Rights Law § 74 (qualified privilege)
- GDPR Art. 6(1)(f), Arts. 15-22, Art. 46
- 18 U.S.C. §§ 1836, 1839 (DTSA)
