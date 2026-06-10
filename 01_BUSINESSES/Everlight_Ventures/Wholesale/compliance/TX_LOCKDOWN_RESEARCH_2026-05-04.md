# TX Wholesale Lockdown — Live Research Findings
**Last Updated:** 2026-05-05 09:45 PT (2026-05-05T09:45:44-07:00)
**Originally Filed:** 2026-05-04 18:30 PT
**Researcher:** Hive web-research dispatch
**Status:** PRE-COUNSEL — Bernard Calloway must verify before any TX live deal

## CRITICAL CORRECTION TO INTERNAL DOCS

The internal `TX_DISCLOSURE_APPENDIX.md` v0.1 references a **"24-month rescission tail"**. This claim is **NOT supported by Tex. Prop. Code §5.0205** (the operative SB 1577 statute), the enrolled SB 1577 bill text, TREC commentary, TRERC commentary, or LoneStarLandLaw analysis published 2024-2026.

If left in any seller-facing outbound, the misrepresentation could itself trigger DTPA exposure. **Bernard must review and either pull the claim or cite the actual statutory source before TX_DISCLOSURE_APPENDIX goes live.**

## Statute basics (verified)

- **Operative section:** Tex. Prop. Code §5.0205 (renumbered from §5.086 in SB 1577)
- **Effective date:** Jan 1, 2024 (NOT 2025 — internal note "passed 2025" is off; bill passed 88R 2023, took effect 2024)
- **Disclosure duty:** Wholesaler must give written disclosure BEFORE assignment contract executes — to (a) end buyer that wholesaler is selling only an option/assignment and does not have legal title, and (b) seller that wholesaler intends to assign.
- **Compliant methods:** (1) "and/or assigns" in original PSA, (2) assignment provision added to PSA, (3) standalone written notice between PSA execution and assignment.
- **Penalty for non-disclosure:** Class A misdemeanor under Occ. Code §1101.758 (unlicensed brokerage), plus common-law fraud / DTPA exposure. **No statutory rescission window.**

## TX wholesaling licensure status (2026)

License **NOT** required if disclosures are made. Tex. Occ. Code §1101.0045 + §5.0205 carve out unlicensed wholesaling provided:
- Wholesaler acts as principal / has equitable interest
- Written disclosure to both seller and end buyer
- No other brokerage acts performed

TREC has not pushed for blanket licensure as of 2026.

## Title partner verification

### 1st Option Title (Garland, TX) — VERIFIED, PRIMARY

- **Address:** 1795 Northwest Hwy, Garland, TX 75041
- **Phone:** 972-271-1700
- **Founder:** Scott Horne (title attorney + active investor, 30+ yrs)
- **Wholesale-friendly:** Explicitly handles double-closes, contract assignments, owner-finance. Quick commitments (days), built around investor flow.
- **RESPA notes:** No public RESPA enforcement found. Reviews positive (Birdeye 25 reviews). Hammer must verify directly: ask for double-close mechanics walkthrough — separate funds, two HUDs, no shortcut funding.

### Patten Title (Houston) — VERIFIED, SECONDARY

- Founded by Ashley Patten (Galleria origin); largest fee-office network in TX.
- Investor-friendly per HouseCashin Houston top-5; mostly positive reviews (one note: ~$200 higher closing costs, occasional doc delay). No RESPA hits.
- **Best fit:** clean double-closes; less ideal for hairy assignment chains.

## TX Cash-Buyer Targets (Hammer's B2B cold-blast — RANKED)

| Rank | Operator | Market | Notes |
|---:|---|---|---|
| 1 | **New Western** | DFW + Houston + FW + Austin + SA | Acquired Big State Houston Oct 2025. 8,200 deals/yr capacity. Best buyer-side absorber. |
| 2 | **REI Nation** | DFW HQ Grapevine + Memphis | ~8K SFR AUM, $1.45B. Direct B2B. |
| 3 | **HomeVestors (We Buy Ugly Houses)** | DFW + Houston franchisees | 1,100+ franchises; Dallas HQ since 1996. Pays 50-70% FMV. **Note:** scrape franchisee list — corporate cold-blast bounces. |
| 4 | **Texas Turnkey Properties** | DFW | Top TX turnkey per Norada 2026. |
| 5 | **CashFlow Texas** | "Texaplex" | Turnkey portfolio builder; cleaner inventory only. |
| 6 | **Maverick Investor Group** | TX statewide | Out-of-state investor channel; passive/turnkey only. |
| 7 | **Southern Hills Home Buyers** | DFW + Houston | Family-owned cash buyer, 5.0 Google. |
| 8 | **Greater Houston Houses** | Houston | 24hr cash offers; 5.0 Google. |
| 9 | **American Home Buyer** | Houston | Active cash buyer site. |
| 10 | **MCB Capital / SFR Growth & Income Fund I** | DFW | Private fund, 2020-formed, DFW SFR-focused. Institutional. |

**DROP from internal seed list:** Norhart (Minnesota multifamily, not TX SFR).

## TX 10-day option period (2026)

- TREC residential contract option period negotiated 3-10 days. **10 days standard in 2026 buyer-leaning market.**
- Buyer pays $200-$500 non-refundable option fee directly to seller.
- **Wholesaler usage:** insist on max option period in PSA + explicit "and/or assigns" language. Option period is the assignment safety window.

## Property Code §5.008 applicability

- §5.008 = Seller's Disclosure of Property Condition (SDN form), required for residential ≤1 dwelling unit.
- **Applies to the SELLER, not the wholesaler.** Original seller delivers SDN to wholesaler-buyer; wholesaler passes SDN through to end buyer on assignment.
- Wholesaler is NOT the §5.008 disclosing party — but the **§5.0205 equitable-interest disclosure IS the wholesaler's duty**. Both must be present in any TX outbound.
- §5.008(e) exemptions (estate, trustee, etc.) — wholesaler still has §5.0205 duty even if no SDN exists from seller side.

## Action items (block live TX deals until done)

1. **Bernard Calloway escalation:** verify §5.0205 disclosure language in `TX_DISCLOSURE_APPENDIX.md`, pull the unsupported "24-month rescission" claim, countersign as v1.0.
2. **Hammer phone-verifies 1st Option Title** — RESPA double-close mechanics walkthrough, then update `state_gates.json` `preferred_closer_id` from `texas_title_dal` to verified ID.
3. **Hammer B2B cold-blast** to top 10 above (use 2026-04-24 Chris-blast template). Goal: 1 anchor + 2 bench in 14 days.
4. **Update `state_advertising_disclaimers.py`** TX entry with §5.0205 verbatim language (replace any §5.086 references — it's been renumbered).
5. **TX 409-lead audit:** purge anything in pipeline where SMS was a prior touch (TX SB 140 violation). Skip-trace top 30 Dallas/Houston code-violation + tax-lien this week.

## Sources

- [Tex. Prop. Code §5.0205](https://texas.public.law/statutes/tex._prop._code_section_5.0205)
- [Tex. Prop. Code §5.008](https://texas.public.law/statutes/tex._prop._code_section_5.008)
- [TRERC: New Texas Assignment Law](https://trerc.tamu.edu/article/new-texas-assignment-law-what-buyers-and-sellers-need-to-know/)
- [SB 1577 88R Enrolled Bill Text](https://capitol.texas.gov/tlodocs/88R/billtext/html/SB01577S.htm)
- [LoneStarLandLaw: Wholesaling in Texas](https://lonestarlandlaw.com/wholesaling-in-texas-real-estate/)
- [TREC: 88th Legislative Update](https://www.trec.texas.gov/article/88th-texas-legislative-session-update-how-it-impacts-license-holders)
- [Tex. Occ. Code §1101.0045](https://texas.public.law/statutes/tex._occ._code_section_1101.0045)
- [1st Option Title](https://www.1stoptiontitle.com/about/)
- [Patten Title](https://pattentitle.com/about-us/)
- [HouseCashin: Investor-Friendly Title Companies Houston](https://housecashin.com/directory/investor-friendly-title-companies/houston-tx/)
- [New Western Acquires Big State (HousingWire, Oct 2025)](https://www.housingwire.com/articles/new-western-acquires-big-state-home-buyers-to-expand-investment-pipeline/)
- [Norada: Best TX Turnkey Markets 2026](https://www.noradarealestate.com/blog/best-turnkey-rental-markets-in-texas-for-out-of-state-investors/)
- [Creekstone: Option Period in Texas (2026)](https://www.creekstonere.com/option-period-texas/)
- [TRERC: Option Period Basics](https://trerc.tamu.edu/article/option-period-basics-2360/)
