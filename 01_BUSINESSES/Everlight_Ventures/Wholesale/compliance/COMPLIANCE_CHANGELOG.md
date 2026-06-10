# Compliance Changelog

> Disclaimer: This file is research and education, NOT legal advice. Consult licensed counsel before relying on any value herein.

Append-only log of changes to the wholesale compliance regime (state_gates.json, disclosure templates, channel strategy, etc.). Date format: YYYY-MM-DD. Sign every entry.

---

- 2026-04-25 -- Added top-level `b2b_vendor_outreach_default` key to state_gates.json with email + manual-voice channels open across all states for vendor outreach (title companies, lenders, attorneys, contractors, JV wholesalers, other professionals). Added `b2b_vendor_outreach_allowed: true` flag to all 9 state blocks (CA, TX, FL, NC, GA, MO, AZ, TN, OH). Added `gate_logic_precedence` to `_meta` documenting that lead_type is checked first: `b2b_vendor` skips consumer-state rules; `seller`/`homeowner`/`homeowner_distress` apply per-state consumer rules. Closes the cadence-gate gap that forced Hammer Knox to drop recipient_state for the Ohio Real Title Agency MOU. -- Justine Park, Compliance Gate.
