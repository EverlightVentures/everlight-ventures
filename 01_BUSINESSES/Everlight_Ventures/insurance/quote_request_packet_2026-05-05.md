# Everlight Ventures -- Commercial Insurance Quote-Request Packet

**Prepared:** 2026-05-05
**Prepared by:** David Wen, Legal Research, Perplexity Intel
**For review by:** Rich Gee, Founder
**Counterparty:** Commercial insurance brokers / underwriters
**Class:** Quote-request packet. Not a binding application. All facts subject to underwriter verification.

---

## Master Cover Letter -- Executive Summary

**To:** Commercial insurance broker
**From:** Rich Gee, Founder, Everlight Ventures
**Date:** 2026-05-05
**Re:** Quote request -- four coverage lines for an early-stage AI-augmented real estate operation

Dear Broker,

Everlight Ventures is a pre-revenue, founder-operated real estate wholesale operation domiciled in California. The operating entity is currently a sole proprietorship. An LLC reinstatement is in progress and is expected to be the named insured at bind. We are seeking quotes on four coverage lines and would like a single broker, where possible, to coordinate the package.

**Operational profile (full detail in section A below):**

- One human founder. Approximately seventy named AI agents handle outreach, contract drafting, compliance review, and audit functions under operator supervision. No human employees.
- Real estate wholesaling, seven-state footprint: Tennessee, Texas, Georgia, Florida, Missouri, Ohio, Arizona.
- Two closed assignments to date, both Tennessee. Purchase and sale agreement prices of $1,800 and $9,520. Assignment fees collected of $700 and $1,428.
- Pre-revenue at the corporate level. Founder operates remotely from a California home office. No client meetings on premises.
- Active outbound-pause until three-party greenlight (compliance officer, operator-of-record, founder).

**Why we are buying coverage now.** A late-April 2026 incident, internally referenced as the Streubel-4435 matter, exposed a gap in our recipient-classification logic: a cold outreach went to an attorney whose name appeared on a property record but who is not the homeowner in any wholesale-relevant sense. The recipient threatened a Better Business Bureau complaint. No claim has been filed. The gap was structural -- an AI-driven outreach pipeline that scored attorneys and government employees as homeowners when their names surfaced on tax rolls. We have published a postmortem, halted outbound, and rebuilt the recipient-resolver. The incident is the proximate reason we are formalizing coverage rather than deferring it to post-revenue. Full postmortem available on request.

**What we have built since.** A four-sink Do Not Contact registrar with daily reconciliation, a recipient-class classifier with hard-block lists for government and attorney domains, per-state outbound gating tied to the relevant statutes (Tennessee SB 909, Texas SB 1577, Arizona HB 2747, with Florida, Georgia, Missouri, and Ohio handled under their respective consumer-protection frameworks), an inbound-watch daemon that catches opt-out signals within five minutes of receipt, and a sender-alias whitelist at the Resend domain layer that prevents legacy scripts from bypassing the brand stack. Documentation list in section H.

**Coverages requested:**

1. Directors and Officers liability, $1M aggregate / $1M per claim, Side A included
2. Errors and Omissions / professional liability, $1M aggregate / $1M per claim, with AI-output endorsement if available
3. Cyber liability and breach response, $1M aggregate, with sub-limits for ransomware, regulatory, and business interruption
4. General liability and a Business Owner's Policy, $1M general / $2M aggregate, including home-office property

We would like to receive indications within fourteen calendar days and bind preferred coverage within thirty calendar days. The full per-coverage requests follow. We are happy to provide any additional documentation listed in section H or answer underwriter questionnaires directly.

Sincerely,

Rich Gee
Founder, Everlight Ventures
California, transitioning LLC
1m.rich.gee@gmail.com

---

## Section A -- Operation Summary (shared across all four quotes)

- **Legal entity at bind:** Everlight Ventures LLC, California (reinstatement pending). Interim sole proprietorship operating under same name.
- **Domicile:** California. Founder home office is the only operating address.
- **Founder and sole human:** Rich Gee. No human employees, no W-2 staff, no 1099 contractors at present.
- **AI workforce:** Approximately seventy named AI agents organized into five squads. Functions include lead sourcing, outbound communications drafting, contract preparation, compliance review, audit, and analytics. All AI outputs that leave the firm are gated through a branded-mailer pipeline that runs a recipient classifier, a state-by-state outbound gate, and a sender-alias whitelist before transmission.
- **Operating footprint:** Wholesale real estate in seven states -- Tennessee, Texas, Georgia, Florida, Missouri, Ohio, Arizona. Tennessee is the sole state where deals have closed.
- **Deal history:** Two closed assignments, both Tennessee. PSA prices of $1,800 and $9,520. Assignment fees of $700 and $1,428. No litigation, no claims, no Better Business Bureau complaints filed against the firm.
- **Revenue stage:** Pre-$25,000 in gross revenue. Pre-Series-A. No outside investors, no advisory board with economic interest, no fiduciary duties to third parties beyond contract counterparties.
- **Risk-relevant incident history:** One. The Streubel-4435 matter, late April 2026. Cold-outbound email to an attorney whose name appeared on a property record. Recipient threatened a Better Business Bureau complaint. No claim filed. Postmortem published internally on 2026-04-26. Outbound paused. Mitigation rebuild is complete pending three-party greenlight.

---

## Quote 1 -- Directors and Officers Liability

**Subject:** Quote request -- Directors and Officers liability for an early-stage AI-augmented real estate operation, California

Dear [Broker name],

I am writing to request an indication on Directors and Officers liability for Everlight Ventures, a one-founder, AI-augmented real estate wholesale operation domiciled in California. The operating entity is a sole proprietorship transitioning to a California LLC at reinstatement. Coverage would be bound under the LLC.

**Operation summary**

- Founder-operated, one human, approximately seventy named AI agents organized into operational squads.
- Real estate wholesaling, seven-state footprint, two closed deals to date, both Tennessee.
- Pre-revenue. Home office in California. No premises liability beyond a single-occupant home office.
- No outside investors. No formally appointed board at this time. An advisory board is contemplated within the next twelve months and is the proximate reason we are structuring D&O coverage now rather than later.

**Coverage requested**

- Limit: $1,000,000 aggregate, $1,000,000 per claim
- Side A coverage included for individual director protection where the company cannot indemnify
- Defense costs outside the limit preferred. Inside-limit defense acceptable if pricing differential is material.
- Deductible: $5,000 to $10,000 acceptable, lower preferred for non-indemnifiable claims
- Retroactive date: inception of the LLC at reinstatement, with prior-acts coverage if available for the sole-proprietorship period
- Premium target: $2,000 to $4,000 annual

**Specific exposures**

- AI-output liability. Approximately seventy AI agents draft outreach, contract terms, and compliance commentary that leaves the firm under the founder's signature. A misstatement, omission, or hallucinated representation by an AI agent is a foreseeable D&O trigger if it is later characterized as a director's breach of duty of care. Coverage should not exclude AI-generated output.
- Real estate wholesaler suit risk. Wholesaling is a litigation-active asset class. Common claim theories include unlicensed brokerage, misrepresentation of assignability, and tortious interference with the underlying purchase contract. We have controls in place (per-state statutory gating, see section A); we are pricing the residual risk.
- Better Business Bureau and state Attorney General complaints. The Streubel-4435 matter put us on notice that a recipient-classification miss can produce a BBB-class complaint. No complaint has been filed; we are pricing the contingent exposure.
- Pre-IPO advisory board exposure. We expect to seat an advisory board within twelve months. Side A coverage for advisors and prospective directors is the operative concern.

**Risk-management controls (premium-mitigating evidence)**

- Outbound communications pause is currently active. Lift requires sign-off from the compliance officer, the operator-of-record, and the founder.
- Four-sink Do Not Contact registrar with daily reconciliation across all outbound channels.
- Recipient-class classifier with hard-block lists for government domains and attorney-firm domain patterns. Built and deployed in response to the Streubel-4435 matter.
- Per-state outbound gating tied to Tennessee SB 909, Texas SB 1577, Arizona HB 2747, with the remaining four states gated under their respective consumer-protection frameworks.
- Inbound-watch daemon classifies and routes opt-out signals within five minutes of receipt.
- Separate compliance-officer assignment per state, with a single accountability owner across all seven.
- Streubel-4435 postmortem is a published, dated, internal artifact, available to underwriters on request.

**Documents available on request**

- Streubel-4435 postmortem (`/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/INBOUND_WATCH_GAPS_2026-04-26.md`)
- Per-state compliance gate matrix
- DNC registrar architecture summary
- LLC formation and reinstatement documentation upon completion
- Founder background and operating biography

**Timeline**

- Indication requested within fourteen calendar days from this email
- Coverage bound within thirty calendar days

I am available for an underwriter call at your convenience. Please confirm receipt and let me know what additional information would speed the indication.

Sincerely,

Rich Gee
Founder, Everlight Ventures (California, transitioning LLC)
1m.rich.gee@gmail.com

---

## Quote 2 -- Errors and Omissions / Professional Liability

**Subject:** Quote request -- Errors and Omissions liability with AI-output exposure, real estate wholesaling, California

Dear [Broker name],

I am writing to request an indication on Errors and Omissions / professional liability coverage for Everlight Ventures. We are an AI-augmented real estate wholesale operation, one human founder, approximately seventy named AI agents, domiciled in California, with deal activity in seven states. This is the coverage line where our AI exposure is most material; the request below reflects that.

**Operation summary**

- Real estate wholesaling, seven-state footprint, two closed assignments to date, both Tennessee, total assignment fees collected of $2,128.
- Approximately seventy AI agents draft outreach, purchase and sale agreements, assignment agreements, and compliance commentary. All outputs that leave the firm are reviewed and signed by the founder. We do not rely on AI signature alone.
- Pre-revenue, no human employees. Sole-proprietorship interim, LLC at reinstatement.

**Coverage requested**

- Limit: $1,000,000 per claim, $1,000,000 aggregate
- AI-output errors endorsement, if available. Embroker and Vouch have offered this in 2025-2026 as a named endorsement; Hiscox, to our knowledge, has not yet offered an equivalent. We are interested in any carrier that can quote AI-output errors as a covered cause of loss rather than an exclusion.
- Real-estate-wholesaler endorsement covering assignment-fee disputes, contract-drafting errors, and coordination errors with title and escrow firms.
- Deductible: $5,000 acceptable, lower preferred where AI-output is the trigger
- Premium target: $1,500 to $3,000 annual

**Specific exposures**

- Assignment fee disputes. The standard wholesaler claim. Buyer or seller alleges the assignment fee was undisclosed, mispresented, or unreasonable. We document fees in the assignment agreement and require buyer acknowledgment, but the residual exposure is not zero.
- Contract drafting errors. Purchase and sale agreements, assignment agreements, and inspection-period addenda are drafted by AI agents and reviewed by the founder before signature. A drafting error that survives review is the canonical E&O claim for this operation.
- AI agent outputs sent under firm name. The Streubel-4435 class. An AI agent produces an outbound communication that misclassifies the recipient or misrepresents the firm's role. This is the named exposure for which we want explicit coverage rather than carrier silence.
- Title firm and escrow coordination errors. Wholesale closings depend on title and escrow workflow. Errors in wire instructions, deed preparation, or closing disclosure handoffs can create vicarious E&O exposure even when the title firm holds primary responsibility.
- Unlicensed brokerage allegations. Wholesalers are not real estate brokers in any of the seven states where we operate, but the line between wholesaler and unlicensed broker is a recurring litigation theme. Tennessee SB 909, Texas SB 1577, and Arizona HB 2747 each define the boundary; we comply with each and document the compliance, but residual claim exposure is not zero.

**Risk-management controls (premium-mitigating evidence)**

- All outbound communications gated through a branded-mailer pipeline with recipient-class classifier and per-state outbound gate. Hard-block lists for government and attorney-firm domains.
- Four-sink DNC registrar with daily reconciliation.
- Outbound pause currently active until three-party greenlight (compliance, operator-of-record, founder).
- Streubel-4435 postmortem published 2026-04-26. Identified five filter gaps and the bypass channel that allowed the send. All five filters have been built and the bypass channel has been closed at the Resend domain layer.
- Inbound-watch daemon catches opt-out and complaint signals within five minutes of receipt and escalates protected-class signals (government, attorney) directly to the compliance officer.
- All AI-drafted contract documents are founder-reviewed and founder-signed. No autonomous contract execution.
- Per-state compliance officers assigned. State-by-state finder-fee threshold confirmed before any close.

**Documents available on request**

- Streubel-4435 postmortem (`/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/INBOUND_WATCH_GAPS_2026-04-26.md`)
- Per-state compliance matrix and statute reference
- Sample purchase and sale agreement (redacted, Tennessee)
- Sample assignment agreement (redacted, Tennessee)
- Recipient-class classifier specification
- AI agent roster and function map
- Founder review and signature workflow documentation

**Timeline**

- Indication requested within fourteen calendar days
- Bind within thirty calendar days

I would like to flag the AI-output endorsement question early. If a carrier in your shop is positioned to quote AI-output as covered rather than excluded, that carrier moves to the front of the evaluation. I am available for an underwriter call.

Sincerely,

Rich Gee
Founder, Everlight Ventures (California, transitioning LLC)
1m.rich.gee@gmail.com

---

## Quote 3 -- Cyber Liability and Breach Response

**Subject:** Quote request -- Cyber liability and breach response for AI-driven small operation, California

Dear [Broker name],

I am writing to request an indication on cyber liability and breach response coverage for Everlight Ventures. Our cyber surface is small in headcount but wide in vendor footprint -- approximately seventy AI agents hold scoped API access to a half-dozen production systems. The exposure profile follows.

**Operation summary**

- One human founder, approximately seventy named AI agents, no human employees.
- California domicile, home-office workstations, cloud-first architecture.
- Pre-revenue, two closed deals to date.
- Vendor stack of record: Supabase (customer property data and contract metadata), Resend (outbound email logs and templates), Stripe (payment data, presently low volume), ImprovMX (inbound email forwarding for forty-two `@everlightventures.io` aliases), Tailscale (mesh networking between operator devices and Oracle production hosts), GitHub (source control and deploy keys), Oracle Cloud (production VMs).

**Coverage requested**

- Aggregate limit: $1,000,000
- First-party coverage: data restoration, ransomware payment, business interruption, cyber extortion response, system damage and forensic costs
- Third-party coverage: customer notification, regulatory response, defense costs, third-party data liability
- Sub-limits requested:
  - Ransomware payment: $250,000
  - Regulatory fines and penalties: $500,000
  - Business interruption: $250,000
  - Notification costs: $100,000 minimum
- Deductible: $5,000 acceptable
- Premium target: $1,500 to $3,000 annual

**Specific exposures**

- Supabase. Holds property records for in-pipeline and closed deals, including seller contact data, address-level property data, and contract metadata. A Supabase compromise is a reportable breach in California under California Civil Code section 1798.82 and in any state where the property record corresponds to a resident.
- Resend. Holds outbound email logs across forty-two firm aliases. A Resend compromise exposes our recipient list, which after the Streubel-4435 matter we treat as a sensitive asset.
- Stripe. Currently low transaction volume. Future revenue at scale moves Stripe to a higher-tier exposure; underwriter should be priced for an environment that scales transaction volume by ten-times within twelve months.
- AI agent API access. Approximately seventy agents hold scoped credentials to one or more of the systems above. Credential compromise of any individual agent is a credible single-point-of-failure scenario. Mitigations are documented; residual exposure is not zero.
- ImprovMX inbound forwarding. Inbound mail traverses ImprovMX before reaching the operator inbox. A forwarding compromise could expose protected-class inbound (government, attorney STOP signals) to a third party.
- Tailscale mesh. Connects operator devices to Oracle production. Compromise of any node in the mesh is a credible lateral-movement vector to production.
- Wire fraud. Wholesale closings depend on wire instructions to title and escrow. Business email compromise targeting wire instructions is the highest-impact cyber exposure for any real estate operation. We require out-of-band verification on every wire, but the residual exposure is not zero.

**Risk-management controls (premium-mitigating evidence)**

- All AI agent credentials are scoped and stored in a single secrets-management layer. No credentials in source. No credentials in chat logs.
- Sender-alias whitelist enforced at the Resend domain layer. Legacy aliases (the `rich@` channel that bypassed the brand stack in the Streubel-4435 matter) have been removed at the domain level, not just at the application level.
- Four-sink DNC registrar with daily reconciliation creates a deterministic record of every outbound recipient.
- Inbound-watch daemon scans IMAP every five minutes for STOP and complaint signals.
- Multi-factor authentication on all human-accessible vendor accounts (Supabase, Resend, Stripe, GitHub, Oracle, ImprovMX, Tailscale).
- Tailscale ACLs limit lateral movement between mesh nodes.
- Wire fraud control: out-of-band verification by phone for every closing wire, against a number obtained from a source other than the email containing the wire instructions.
- Daily Supabase backup with off-site retention.

**Documents available on request**

- Vendor inventory and data-flow diagram
- AI agent roster with credential-scope map
- Streubel-4435 postmortem
- Tailscale ACL configuration summary
- Wire-fraud control procedure
- Supabase backup verification log

**Timeline**

- Indication requested within fourteen calendar days
- Bind within thirty calendar days

If your shop has experience with AI-vendor-heavy small operations (Embroker, Vouch, and Coalition all have product fit here), please flag that in the response. I am available for an underwriter call.

Sincerely,

Rich Gee
Founder, Everlight Ventures (California, transitioning LLC)
1m.rich.gee@gmail.com

---

## Quote 4 -- General Liability and Business Owner's Policy

**Subject:** Quote request -- General liability and BOP for home-office real estate operator, California

Dear [Broker name],

I am writing to request an indication on a General Liability policy or Business Owner's Policy for Everlight Ventures. Our premises and physical-world exposure is light. The package is intended to round out the four-coverage program described in our cover letter.

**Operation summary**

- One human founder, home office in California. No commercial premises.
- Real estate wholesale, seven states. Two closed deals, both Tennessee.
- Property walks and site visits occur but are infrequent (under twenty per year projected).
- No client meetings on premises. Meetings, when they occur, are at the property, at a title office, or remote.

**Coverage requested**

- General liability: $1,000,000 per occurrence, $2,000,000 aggregate
- Property: home-office equipment (laptops, displays, networking, peripherals), estimated replacement value $15,000 to $20,000
- Premises: home office, California
- Personal and advertising injury included
- Hired and non-owned auto, if available as an endorsement, for occasional rental-vehicle use during property walks
- Deductible: $1,000 acceptable
- Premium target: $500 to $1,500 annual

**Specific exposures**

- Property-walk site visits. Infrequent but unavoidable in wholesale. The risk is bodily injury to the founder or to a third party during a walk, slip-and-fall on uneven property, or alleged property damage caused during inspection.
- Advisor visits. If advisors visit the home office in the next twelve months, premises liability for that visit becomes live. Currently zero advisor visits projected, but coverage should not exclude.
- Personal and advertising injury. Wholesaling generates outbound communications volume; defamation, libel, and copyright-style claims are foreseeable, particularly given the AI-driven nature of outbound.
- Cyber and AI exposure are NOT requested under this line; covered separately under quote 3 and quote 2.

**Risk-management controls**

- Home office is single-occupant, no public ingress.
- Property walks performed by the founder personally, no contractor or employee delegation.
- All outbound communications gated through controls described in quotes 1, 2, and 3.

**Documents available on request**

- Home office inventory list
- Founder driver record (if hired and non-owned auto is in scope)
- Per-state operations summary

**Timeline**

- Indication requested within fourteen calendar days
- Bind within thirty calendar days

This is the lowest-complexity line in the package. I would prefer to bind it together with the other three under one broker if pricing is competitive.

Sincerely,

Rich Gee
Founder, Everlight Ventures (California, transitioning LLC)
1m.rich.gee@gmail.com

---

## Section H -- Documents Available on Request (consolidated)

The following internal artifacts are available to any underwriter performing due diligence. All paths below are under the operator's local workspace and will be packaged as PDF on request.

1. Streubel-4435 postmortem -- `/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/INBOUND_WATCH_GAPS_2026-04-26.md`
2. Per-state compliance gate matrix (Tennessee SB 909, Texas SB 1577, Arizona HB 2747, plus FL/GA/MO/OH consumer-protection summaries)
3. Recipient-class classifier specification
4. Inbound-watch daemon specification (referenced in Streubel-4435 postmortem, section g)
5. Four-sink DNC registrar architecture and daily reconciliation procedure
6. AI agent roster, function map, and credential-scope summary
7. Sample purchase and sale agreement (redacted, Tennessee)
8. Sample assignment agreement (redacted, Tennessee)
9. Vendor inventory and data-flow diagram
10. Wire-fraud control procedure
11. LLC formation and reinstatement documentation upon completion
12. Founder background and operating biography
13. Two closed-deal summaries (Tennessee)

---

## Section I -- Operator Notes for Rich (not for transmission)

These notes do not go to the broker. They are reminders before sending.

- Confirm the LLC reinstatement status before sending. If still pending, the cover letter language is correct as drafted; if reinstated, replace "California, transitioning LLC" with the post-reinstatement entity name.
- The premium targets are operator estimates, not broker promises. Carriers may quote materially above or below. Do not anchor to the targets in negotiation; let the broker land their own number first.
- Embroker and Vouch are the most likely carriers to offer AI-output endorsements as of early 2026. If a broker quotes E&O without addressing AI-output explicitly, ask the question directly.
- The Streubel-4435 postmortem is the best risk-mitigation evidence in the packet. Do not hide it. Disclose it in the first email if asked, and offer the document proactively. Underwriters reward operators who self-disclose with documented controls; they punish operators who try to bury near-misses and have them surface in a questionnaire.
- Replace `[Broker name]` placeholders with the actual broker contact name before sending. Personalize the first paragraph if a prior conversation has occurred.
- This packet is research and template work product. It is not legal advice. Recommend a licensed insurance broker and counsel review before transmission, particularly around the AI-output endorsement language and the prior-acts coverage request.

---

**Citation block:**

- California Civil Code section 1798.82 (data breach notification, California)
- Tennessee SB 909 (Tennessee wholesale and consumer-protection framework, in force 2025)
- Texas SB 1577 (Texas wholesale framework, in force 2025)
- Arizona HB 2747 (Arizona wholesale framework, in force 2025)

Citations current as of 2026-05-05. All statute references should be verified against the latest enrolled text by the receiving broker's underwriter; statutes in this space have moved quickly in 2024-2026.

Prepared by David Wen, Legal Research, Perplexity Intel, Everlight Ventures.
