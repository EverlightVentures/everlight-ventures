# Cipher Batch -- Memphis Seller Intel
**Date:** 2026-04-29 | **Reporter:** Christopher "Cipher" Wolfe (Perplexity Intel)
**Editor:** Bernard "Brief" Calloway | **Verifier:** Thomas "Tally" Rourke
**Scope:** 14 priority parcels from the 30-keeper batch (9 absentee out-of-state + 5 SFRs in Chris's buy-box)
**Method:** `seller_intel_deepdive.py` + targeted WebSearch enrichment
**Privacy floor:** Public-record only. No protected-class profiling. Situational signals only.

---

## Compliance gate (Justine Burns review notes)
- All 14 are TN-based property; TN allows email + mail. Cold SMS NOT used. Phone calls limited to 8am-9pm local-to-RECIPIENT (per state_gates.json, 60-min buffer applied).
- 6 leads have non-TN owner mailing -- phone hours are calculated against OWNER timezone, not Memphis.
- TS2202 status (4+ year tax-delinquency cohort) is public TN record. Citing it in mail is permitted; citing it in cold call must be neutral framing ("I see the parcel has been on the back-tax list").
- Ministry/church owners (#4, #13): no faith-based language in pitch; treat as institutional owner.

---

## Signal Distribution (snapshot)

| Signal | Count | Notes |
|---|---|---|
| Absentee out-of-state | 9 | Highest motivation cohort |
| Absentee in-state (TN, not Memphis) | 2 | Cordova + Nesbit MS |
| Owner-occupied or local-Memphis | 5 | SFRs in buy-box |
| Estate (probate active or pending) | 1 | Howard Eddie -- TX mailing |
| LLC/Corp owner | 1 | Greater Love Ministries |
| Religious-org owner | 2 | Greater Love + Carnegie COGIC |
| Long-term owner (>=20yr) | 5 | Howard, Jones/Saunders, Green, Toby Jones, Showers |
| TS2202 (4+ years tax-delinquent) | 14/14 | Entire batch |
| Apartment / shared-housing mailing | 1 | Trezden Matthews (Cobb Pkwy unit 3123) |
| Vacant lot | 9 | Per assessor classification |

---

## Lead-by-Lead Brief (1 paragraph each)

### ABSENTEE OUT-OF-STATE (highest motivation -- lead with these)

**1. 117 FARROW AVE -- HOWARD EDDIE (Estate of), San Antonio TX -- parcel 024057  00012**
Howard Eddie estate, vacant lot, 21 yrs in family, $3,800 appraised, 4+ yrs tax-delinquent, executor mails out of San Antonio. This is the cleanest motivation profile in the batch -- estate + out-of-state + back-tax + low-value lot = executor wants it gone. Decedent obit did not surface in legacy.com / dignitymemorial public archives (Eddie Howard from 1981/2005-era Memphis is too common a name for a clean WebSearch hit), so heir-mapping needs a Shelby County Probate browser pull (CRITICAL queue item already in `intel.md`). **Pitch hook:** `estate_burden_relief` -- "We close direct with the executor in 14 days, no out-of-pocket cost to the estate, we pay every dollar of back tax at closing." **Channel:** Email-first to any address Hammer can find via Shelby Probate executor record. Phone follow-up permitted in San Antonio TX timezone (CT) -- 8am-9pm CT, NOT Memphis time. If no email surfaces, mail piece via Lob direct-to-executor as soon as Probate Court yields the executor name.

**2. 108 E OLIVE AVE -- LEGGETT BENNIE JR, Los Angeles CA -- parcel 024055  00038**
Vacant lot, $3,500 appraised, owned 7 yrs after a 2019 quitclaim chain (likely inherited / family transfer at $601 nominal price), 4+ yrs back-tax. CA mailing 90011 = South-Central LA. Profile reads "inherited Memphis lot, never visited, no plan, watching tax bills accumulate." **Pitch hook:** `outofstate_convenience` + `back_tax_relief` -- "Managing a Memphis property from LA is its own kind of work. We pay every dollar of back tax at closing -- you don't owe a dime out of pocket." **Channel:** Email-first; LA phone hours 8am-9pm PT for follow-up. This one is high-conversion-probability if we can surface an email.

**3. 1430 SILVER -- JONES CHRISTINE & MAGGIE SAUNDERS, Oakland CA -- parcel 048034  00013**
Vacant lot, $5,400 appraised, two-name title (joint owners or co-heirs), 28-yr hold, 4+ yrs back-tax. Long ownership + co-owner + Oakland mailing = classic "we both inherited it, neither of us wants to deal with it" pattern. **Pitch hook:** `long_ownership_dignified_close` + `outofstate_convenience` -- "You've held this property for 28 years. Memphis values have shifted; carrying costs haven't. We can close clean and quick, by mail and wire." **Channel:** Email-first to BOTH names if surfaced (co-ownership requires both signatures). Phone follow-up Oakland CA hours, 8am-9pm PT. Tally to verify joint-tenancy vs tenancy-in-common via Register of Deeds before any executed offer.

**4. 1537 WILSON ST -- GREATER LOVE FOR LIFE MINISTRIES INC, Albuquerque NM -- parcel 048003  00007**
Religious-org + LLC, vacant lot, $7,000 appraised, 9-yr hold, 13-deed sales history (heavy turnover before this owner), 4+ yrs back-tax, PO Box mailing in Albuquerque. WebSearch did not match this exact ministry name in Albuquerque public nonprofit databases -- could be unregistered, dissolved, or a satellite of a larger ministry. The PO Box mailing across state lines + tax delinquency = ministry holding surplus real estate that's not central to mission, exactly the script's `ministry_clean_close` profile. **Pitch hook:** `ministry_clean_close` (no faith language; institutional framing) -- "Cash, no commission, 14-day close. Frees the funds for the work that matters." **Channel:** Mail to PO Box first (ministries respond to letterhead better than email); if EIN/officer surfaces via NM Sec of State public registry, email the registered agent. Phone follow-up Albuquerque MT hours, 9am-5pm MT.

**5. 1393 VALSE -- TREZDEN MATTHEWS, Kennesaw GA -- parcel 060067  00007**
Vacant lot, $4,900 appraised, 6-yr hold, $100 quitclaim entry-price (inherited or family transfer), 4+ yrs back-tax. Mailing is an apartment unit (3050 Cobb Pkwy NW Apt 3123) -- this is a shared/rental address, not a homeowner. Profile reads "younger owner, inherited the lot, lives in apartment in Atlanta metro, no real estate sophistication, just paying tax notices." **Pitch hook:** `modest_residence_simple_offer` + `back_tax_relief` -- frame for clarity not sophistication. "Cash, in your hand at closing. We pay the back tax. We mail the offer + closing paperwork. Fourteen days." **Channel:** Email-first if surfaced; mail to the apartment is risky (apt-3123 may forward inconsistently). Phone follow-up Kennesaw GA hours 8am-9pm ET.

**6. 1329 MICHIGAN ST -- FRANKLIN KEMP, Ellenwood GA -- parcel 024055  00028**
Vacant lot, $3,300 appraised, 6-yr hold, 2020 quitclaim acquisition (inherited or transferred at $0), 4+ yrs back-tax. Ellenwood is south Atlanta metro, single-family-home zip. Profile: "inherited from family, owns home in Atlanta, low Memphis tie." **Pitch hook:** `outofstate_convenience` + `back_tax_relief`. **Channel:** Email-first; mail to home address is reliable; phone follow-up Ellenwood GA 8am-9pm ET. Worth running this address through Shelby Register of Deeds for portfolio-check -- if Kemp owns multiple Memphis lots, package-pitch.

**7. 1112 SAXON -- JOSEPH SPILMANN JR, Carriere MS -- parcel 026013  00022**
Vacant lot, $8,000 appraised (highest of the lot-only group), 6-yr hold, multi-quitclaim acquisition pattern ($200, $801, $500, $1,800 over 2017-2020 = portfolio-builder accumulating cheap tax-delinquent lots), 4+ yrs back-tax. This profile reads INVESTOR, not retail owner -- the $200/$500 quitclaims are wholesaler/back-tax-buyer pattern. **Pitch hook:** `investor_to_investor` if Tally confirms portfolio via Shelby ROD. "Saw the QC chain. Investor-to-investor. Happy to package this with any other Memphis lots if you're thinning inventory." **Channel:** Email-first; investor profile responds to crisp investor-to-investor copy, not empathy. Phone follow-up Carriere MS (CT) 8am-9pm CT.

**8. 1303 MICHIGAN ST -- IMMANUEL STOKES, Nesbit MS -- parcel 024055  00017**
Vacant lot, $3,200 appraised, 6-yr hold via $220 quitclaim (inherited / transferred), 4+ yrs back-tax. Nesbit MS is 38651 -- DeSoto County, just south of Memphis-Shelby border, ~25 min drive to property. This owner can physically reach the property; mailing is in-state but out-of-Memphis. **Pitch hook:** `back_tax_relief` (script's only fit) plus `vacant_lot_quick_cash` -- "We see the property's been on the back-tax list. We pay every dollar at closing. 14 days, you walk clean." **Channel:** Email-first if surfaced; door-knock is feasible given proximity but reserve that for after mail/email don't land. Phone follow-up Nesbit MS (CT) hours.

**9. 1539 S ORLEANS ST -- SAMANTHA GREEN, Cordova TN -- parcel 034033  00003**
Vacant lot, $7,000 appraised, 24-yr hold (acquired 2002 at $17,500), 4+ yrs back-tax, mailing is a Germantown Pkwy STE 101-301 (commercial mailbox / mail-receiving service). The commercial mailbox mailing + 24-year hold + tax delinquency = "owner has moved on, retains property, uses commercial mailbox to manage from a distance even though technically in TN." Long ownership is the lever. **Pitch hook:** `long_ownership_dignified_close` -- "You've held this for 24 years. Memphis values have shifted, carrying costs haven't. We can offer a clean, no-surprise close." **Channel:** Mail-first to the commercial mailbox (it forwards reliably -- that's its purpose); email if surfaced. Phone follow-up Cordova TN (CT) hours.

---

### SFRs IN CHRIS'S BUY-BOX

**10. 1596 GABAY ST -- TOBY JONES, mailing TBD (3772 Socorro) -- parcel 034042  00014 -- yb 1940, $22,700**
SFR built 1940, 21-yr hold, $22,700 appraised, 4+ yrs back-tax, **mailing city/state/zip blank in our DB** -- "3772 Socorro" alone is ambiguous (could be Socorro NM, Socorro TX, or a Memphis street -- needs Tally cross-check at Shelby ROD before any outreach). 14-deed sales history shows this property has churned through quitclaims and deeds-of-trust (financial pressure or family transfers across decades). **Pitch hook:** `long_ownership_dignified_close` + `back_tax_relief`. **Channel:** **DO NOT email or mail until Tally resolves the mailing city.** Hold this lead 24-48 hrs pending verification. After verified, treat as a likely-El-Paso-TX or Socorro-NM absentee, treat as #1-9 cohort.

**11. 1536 S THIRD ST -- HAKEEM MIKAL L, Memphis TN 38125 -- parcel 035093  00032 -- yb 1968, $23,800**
SFR built 1968, $23,800 appraised, 7-yr hold (acquired 2019 via QC), 4+ yrs back-tax, owner mailing is Memphis 38125 (Hickory Hill / Whitehaven east area, ~10 mi from property). 12-deed history shows turnover including $55,600 sale in 2006 and $55,000 court-deed in 2003. Owner-occupied or local-investor profile. **Pitch hook:** `back_tax_relief` -- "We see the property's been on the back-tax list for a few years. We pay every dollar of back tax + penalty at closing, out of OUR side." **Channel:** Email-first; mail to 38125 home address as backup. Phone follow-up Memphis TN (CT) 8am-9pm CT. Higher friction than absentee cohort -- local owners have more options and less urgency. Lead with the clean-close framing, not estate empathy.

**12. 1250 DUNNAVANT ST -- MARCO WILLIAMS, Memphis TN 38106 (1241 Dunnavant) -- parcel 026056  00056 -- yb 1951, $40,000**
**HIGHEST DEAL-QUALITY TARGET in this batch.** SFR built 1951, $40,000 appraised, 12-yr hold, 4+ yrs back-tax, **owner mailing is 1241 Dunnavant -- across the street from the subject property at 1250 Dunnavant**. Owner lives in his other Dunnavant property. Likely scenario: this is a rental he can't rent (tax-delinquent + 1951 build = condition concerns), or inherited / picked up cheap, or family-transfer leftover. Owner-name in DB is "WLLIAMS MARCO" (typo missing the I) -- Tally to confirm spelling at the Register. The proximity (across-the-street) is the strongest in-person-meeting opportunity in the batch. **Pitch hook:** `back_tax_relief` + door-knock. **Channel:** **Email-first per doctrine, but this lead specifically warrants a door-knock follow-up given the literal across-the-street mailing.** Mail to 1241 Dunnavant. Phone Memphis CT hours. If Hammer can be at 1241 Dunnavant in person, the conversation rate jumps; this is the one in the batch where physical presence justifies the gas.

**13. 1577 MCMILLAN ST -- CARNEGIE CHURCH OF GOD IN CHRIST, mailing TBD (5340 Santa Monica St) -- parcel 034026  00014 -- yb 1992, $56,000**
SFR built 1992, $56,000 appraised (highest in batch), 17-yr hold, 4+ yrs back-tax, religious-org owner. **Critical WebSearch enrichment:** Carnegie Church of God in Christ rebranded to **Gloryland COGIC** and operates from **1584 Carnegie St**, NOT 1577 McMillan. The McMillan parcel is **NOT their active worship site -- it is surplus property the church is holding while paying property tax on it for 4+ years.** This sharpens the pitch from "buy your church" (sensitive) to "free up the surplus parcel" (institutional, clean). Mailing in DB is "5340 Santa Monica St" with no city -- could be CA, FL, or local; Tally to resolve. **Pitch hook:** `ministry_clean_close` -- "Ministries sometimes end up holding lots that aren't central to the mission. We close clean and quick, freeing the funds for the work that matters." **Channel:** Mail-first to the church's current operating address (1584 Carnegie St, Memphis 38106) since the DB mailing is unresolved -- letters to the active church reach the trustee/pastor reliably. Email if a board contact surfaces via TN Sec of State nonprofit registry. Phone Memphis CT hours, daytime preferred (admin-staffed, not pastoral hours).

Sources for #13 enrichment:
- [Carnegie Church of God in Christ - Yelp listing](https://www.yelp.com/biz/carnegie-church-of-god-in-christ-memphis)
- [Carnegie Church of God in Christ - Hub.biz directory](https://carnegie-church-of-god-in-christ.hub.biz/)
- [Carnegie Church of God in Christ - Church Finder](https://www.churchfinder.com/churches/tn/memphis/carnegie-church-god-christ)

**14. 1382 FLORIDA ST -- SHOWERS PETER JR & LOLITA SHOWERS, Memphis TN 38109 -- parcel 024047  00022**
SFR (build year not in this slice but $13,900 appraised), 24-yr hold (acquired 2001-2002), 4+ yrs back-tax, joint married-couple title, owner mailing is Memphis 38109 (South Memphis / Whitehaven). Long-term local owners, retain another Memphis property as primary residence. **Pitch hook:** `long_ownership_dignified_close` + `back_tax_relief` -- "You've held this for 24 years. Memphis values have shifted; the cost of carrying property has not. We pay every dollar of back tax at closing." **Channel:** Email-first if surfaced; mail to 465 Bonnell Ave (38109) as primary; phone Memphis CT hours. Joint title means BOTH signatures required on any executed offer; address letter to "Peter & Lolita Showers" not just one.

---

## Cipher's Tier-Ranking (highest dispatch priority first)

1. **#12 Marco Williams (1250 Dunnavant)** -- across-the-street owner + $40k SFR + door-knockable. Hammer's first stop.
2. **#1 Howard Eddie Estate (117 Farrow)** -- cleanest estate motivation, just need probate executor name.
3. **#13 Carnegie COGIC (1577 McMillan)** -- highest $appraised + surplus-property profile + clean institutional pitch. Letterhead to 1584 Carnegie St.
4. **#9 Samantha Green (1539 S Orleans)** -- 24-yr hold, commercial mailbox, dignified-close hook fits perfectly.
5. **#3 Jones / Saunders (1430 Silver)** -- 28-yr hold, co-ownership, Oakland mailing -- two-signature scenario but motivation is high.
6. **#7 Joseph Spilmann Jr (1112 Saxon)** -- investor-to-investor pitch, package-deal potential, $8k highest-value lot.
7. **#14 Showers (1382 Florida)** -- 24-yr local married-couple, dignified close.
8. **#4 Greater Love Ministries (1537 Wilson)** -- ministry surplus, mail to PO Box.
9-14. Remaining 6 -- standard out-of-state cohort, run through Piper's templated email-first sequence.

---

## Items requiring Tally verification before executed outreach
- #10 Toby Jones: resolve mailing city/state/zip for "3772 Socorro" via Shelby ROD.
- #12 Marco Williams: confirm name spelling (DB has "WLLIAMS MARCO" -- likely typo) before printing on letterhead.
- #13 Carnegie COGIC: resolve "5340 Santa Monica St" mailing -- verify it's a real mailing address vs DB artifact, and pull current trustee/board officer via TN Sec of State nonprofit registry.
- #1 Howard Eddie: pull Shelby County Probate Court record for executor name + address. CRITICAL before any outreach.

## Items Brief Calloway should pre-clear
- All ministry/church framing (#4, #13) -- no faith-based copy, institutional framing only.
- All estate framing (#1) -- empathy-led, never references decedent personal details.
- Any cold-call script for the 6 out-of-state owners -- Justine state_gates buffer (8am-9pm LOCAL-TO-RECIPIENT, not Memphis).

---

## Channel Distribution Summary (per-lead, email-first per doctrine)

| # | Lead | Primary | Backup | Phone hours |
|---|---|---|---|---|
| 1 | Howard Estate | Email (post-probate) | Mail to executor | 8a-9p CT (San Antonio) |
| 2 | Leggett | Email | Mail | 8a-9p PT (LA) |
| 3 | Jones/Saunders | Email | Mail (both names) | 8a-9p PT (Oakland) |
| 4 | Greater Love Ministries | Mail (PO Box) | Email if officer surfaces | 9a-5p MT (Albuquerque) |
| 5 | Matthews | Email | -- (apt mail unreliable) | 8a-9p ET (Kennesaw) |
| 6 | Kemp | Email | Mail | 8a-9p ET (Ellenwood) |
| 7 | Spilmann | Email (investor copy) | Mail | 8a-9p CT (Carriere) |
| 8 | Stokes | Email | Mail / drive-by | 8a-9p CT (Nesbit) |
| 9 | Green | Mail (commercial box) | Email | 8a-9p CT (Cordova) |
| 10 | Toby Jones | **HOLD pending Tally** | -- | -- |
| 11 | Hakeem Mikal | Email | Mail | 8a-9p CT (Memphis) |
| 12 | Marco Williams | Email + door-knock | Mail | 8a-9p CT (Memphis) |
| 13 | Carnegie COGIC | Mail to 1584 Carnegie St | Email if officer surfaces | 9a-5p CT (Memphis admin) |
| 14 | Showers | Email | Mail (both names) | 8a-9p CT (Memphis) |

---

## Generated artifacts
- 14 individual `intel.md` files at `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/seller_intel/{parcel_safe}/intel.md`
- 14 corresponding `intel.json` (structured signals + browser_queue + pitch_hooks)
- This consolidated batch summary: `CIPHER_BATCH_2026-04-29.md`

## Hand-off
- **Brief Calloway** -- approve cohort framing + the 4 holds-for-Tally
- **Tally Rourke** -- 4 verifications listed above (Toby Jones mailing, Williams spelling, Carnegie mailing + officer, Howard Eddie probate)
- **Piper Reeves** -- email-first sequencing per channel table; 9 sends ready (#2,#3,#5,#6,#7,#8,#11,#14 + post-Tally #1)
- **Hammer Calloway** -- door-knock #12 Marco Williams (across-the-street); secondary #8 Stokes (25-min drive from Nesbit)
- **Justine Burns** -- compliance pre-clear on the 3 cohorts (estate, ministry, multi-state phone hours)

---

_Reporter: Cipher | Editor: Brief | Verifier: Tally | "Chain confirms. Shipping the write-up."_
