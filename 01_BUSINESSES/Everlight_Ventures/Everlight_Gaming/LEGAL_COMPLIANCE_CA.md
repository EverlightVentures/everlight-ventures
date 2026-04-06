# LEGAL COMPLIANCE SUMMARY: California Social Casino & Pay-to-Play Arcade Games

**Entity:** Everlight Logistics LLC (California)
**Date:** March 6, 2026
**Status:** RESEARCH MEMO -- NOT LEGAL ADVICE. Consult a licensed California attorney before launch.

---

## 1. IS THIS MODEL LEGAL IN CALIFORNIA?

**Short answer: Most likely yes, with careful structuring.**

Your model (pay $0.25-$2.99 for access/lives/hands, win virtual chips with zero cashout value) removes the "prize" element from the three-element gambling test. Under California law, illegal gambling requires ALL THREE simultaneously:

1. **Consideration** (payment of money) -- PRESENT
2. **Chance** (outcome determined by luck) -- PRESENT in blackjack
3. **Prize** (something of value awarded) -- ABSENT if chips have no redemption value

**If any one element is missing, it is not gambling under California law.**

### Key Statutes

- **Cal. Penal Code 330**: Prohibits banking games "played for money, checks, credit, or other representative of value." If virtual chips cannot be redeemed, this should not apply.
- **Cal. Penal Code 330b**: Defines slot machines; exempts "pinball and other amusement machines or devices, which are predominantly games of skill."
- **Cal. Penal Code 332**: Prohibits obtaining money by fraudulent gaming. Not applicable if no money changes hands as winnings.

### AB 831 -- Sweepstakes Casino Ban (Effective January 1, 2026)

AB 831 banned "sweepstakes casinos" using dual-currency models with cash redemption. **This does NOT ban your model** because:
- AB 831 targets platforms where virtual currency CAN be redeemed for real money
- Pure social casinos with no cash redemption are explicitly NOT covered
- Your model has no sweepstakes component and no cashout mechanism

---

## 2. REQUIRED DISCLAIMERS AND TERMS

### Display on every page and in purchase flow:

"This is a social entertainment platform. Virtual chips have NO real-money value and cannot be redeemed, exchanged, transferred, or cashed out for real money, goods, or services. Purchases are for entertainment access only. This is NOT gambling."

### Terms of Service must include:
- Virtual chips have zero monetary value, non-transferable
- No cashout/redemption mechanism exists or will exist
- Purchases are for entertainment access only
- Prohibition on third-party chip selling/buying
- Refund policy compliant with CA Consumer Protection laws

---

## 3. CLASSIFICATION: ENTERTAINMENT, NOT GAMBLING

- Players pay for ACCESS (hands, lives, sessions), not for chance to win value
- Virtual chips are a SCORE MECHANIC, not a prize
- Card battler (Alley Kingz): skill-based arcade -- LOW risk
- Blackjack: chance-based but no prize element -- MEDIUM risk

---

## 4. KEY CA CODE SECTIONS

| Code | Section | Relevance |
|------|---------|-----------|
| Cal. Penal Code | 330 | Core anti-gambling; prohibits banking games played for value |
| Cal. Penal Code | 330b | Slot machine definition; exempts skill-based amusement |
| Cal. Penal Code | 330-337z (AB 831) | Sweepstakes ban; does NOT cover no-cashout social games |
| Cal. B&P Code | 17200 | Unfair Competition Law (consumer protection) |
| Cal. B&P Code | 17500 | False advertising prohibition |
| Cal. B&P Code | 19800-19987 | Gambling Control Act (not applicable if not gambling) |
| Federal | COPPA | Children's online privacy if under-13 users possible |

---

## 5. AGE MINIMUM: SET TO 18+

Even though 13+ may be technically permissible, 18+ is strongly recommended:
- Eliminates COPPA compliance burden entirely
- Removes argument of targeting minors with gambling-adjacent content
- Aligns with industry standard (Zynga Poker, Big Fish all use "adult audiences")
- Stronger legal defense if gambling classification is challenged
- Avoids CA Age-Appropriate Design Code (AB 2273) burdens for under-18 services

---

## 6. LICENSES AND REGISTRATIONS

### No gambling license required -- because it is not gambling.

### You DO need:
- California LLC registration (DONE: Everlight Logistics LLC)
- California Seller's Permit (digital goods may qualify)
- Sales tax collection on digital entertainment purchases (consult tax professional)
- Privacy Policy (required under CalOPPA)
- PCI-DSS handled via Stripe (do not store card data)

---

## 7. PRECEDENT

### Zynga Poker -- FAVORABLE
- Operates legally in CA selling virtual chips for real money
- Chips have NO cashout value, classified as entertainment
- Not affected by AB 831

### Big Fish Casino -- CAUTIONARY
- Kater v. Churchill Downs (9th Circuit, 2018): Court held virtual chips were a "thing of value" under WASHINGTON law because pay-to-continue loop was functionally gambling
- Settlement: $155 million
- CRITICAL: This was Washington law, not California. But 9th Circuit reasoning is influential.

### Mitigation from Big Fish:
**Always offer a free-play path.** Daily free chips, cooldown timers, or other non-paid ways to continue. Never force a purchase to keep playing.

---

## 8. RISK MITIGATION CHECKLIST

- [ ] Virtual chips have ZERO redemption/cashout value
- [ ] No secondary market for chips (prohibit in TOS)
- [ ] No "pay-to-continue" trap -- offer free play paths (daily free chips)
- [ ] 18+ age gate with date-of-birth verification
- [ ] Clear disclaimers on every screen
- [ ] TOS reviewed by California gaming/entertainment attorney
- [ ] Privacy Policy compliant with CalOPPA and CCPA
- [ ] No marketing language implying real-money gambling
- [ ] PCI-DSS handled via Stripe
- [ ] Sales tax compliance for digital purchases

---

## 9. RISK ASSESSMENT

| Factor | Risk | Notes |
|--------|------|-------|
| Card Battler (score-based) | LOW | Skill game, no chance, clear entertainment |
| Blackjack (virtual chips, no cashout) | MEDIUM | Chance-based but no "prize" element |
| AB 831 compliance | LOW | No sweepstakes/cashout component |
| Age-related liability | LOW | 18+ gate eliminates most risk |
| Class action exposure | MEDIUM | Strong TOS and disclaimers essential |

**Recommendation:** Budget $2,000-$5,000 for a CA gaming attorney to review TOS/Privacy Policy and issue a formal legal opinion letter before launch.

---

*Research memo for internal planning. Not legal advice. Retain a licensed California gaming/entertainment attorney before launch.*
