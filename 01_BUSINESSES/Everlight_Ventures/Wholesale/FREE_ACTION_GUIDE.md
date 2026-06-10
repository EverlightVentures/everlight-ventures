# Free-Tier Action Guide -- Everlight Ventures Wholesale

The audit gaps that need real-world setup but cost nothing or near-nothing. Each item: what to do, where, expected time.

---

## 1. Google Business Profile (Atlanta, GA)

**Cost:** Free.
**Time:** 30 minutes + verification wait (postcard or phone, 3-7 days).
**Why:** GBP is the single highest-leverage local SEO move for any service business. Your name shows up on Google Maps, in "wholesale houses Atlanta" searches, and qualifies you for review collection.

**Steps:**

1. Go to https://business.google.com/create
2. Sign in with the Gmail account you use for the business (1m.rich.gee@gmail.com)
3. Business name: **Everlight Ventures**
4. Category: **Real estate agency** (closest available to "wholesaler")
5. Service area: pick "I deliver goods and services to my customers" → add Atlanta + 25-mile radius
6. Phone: **+1 (404) 800-4380** (your new Twilio number)
7. Website: **https://everlightventures.io**
8. Verification: Google will offer postcard, phone, or video. Phone is fastest.

**After verified:**

- Add 5+ photos (logo, your face, sample marketing materials, an Atlanta property, your Slack dashboard)
- Write a description using these keywords: "off-market cash buyer Atlanta", "we buy houses fast cash close 14 days", "real estate investment firm"
- Set hours: Mon-Sat 8 AM - 9 PM
- Turn on messaging
- Request reviews from your first 3 closes (legally; do NOT incentivize)

---

## 2. LLC Foreign Filing Tracker (8 states)

**Cost:** $50-$300 per state filing fee, one-time + annual report fee ($25-$50/yr per state).
**Time:** 1 hour per state for online filings.
**Why:** Per memory, Everlight Logistics LLC is registered in one home state. To do business legally in additional states (sign contracts, take EMD, close on properties), you need to register as a "foreign LLC" in each.

**Status tracker (fill in as you go):**

| State | Foreign filing status | Date filed | Annual report due | Registered agent |
|-------|----------------------|------------|-------------------|------------------|
| GA | TBD | | | |
| FL | TBD | | | |
| TX | TBD | | | |
| AZ | TBD | | | |
| CA | TBD | | | |
| MO | TBD | | | |
| NC | NOT FILING -- wholesale blocked per HB 797 | n/a | n/a | n/a |
| TN | TBD | | | |

**How to file each:**

1. Get a Certificate of Existence (also called "Certificate of Good Standing") from the home state where Everlight Logistics is registered.
2. Visit the foreign-state's Secretary of State website. Filing forms are usually under "Business Filings" → "Foreign LLC Registration" or "Application for Authority."
3. Complete online form. You'll need:
   - Home state name + LLC name
   - Date of original formation
   - Principal business address
   - Registered agent in the foreign state (use Northwest Registered Agent or Harbor Compliance for ~$125/yr per state if you don't have a contact there)
   - Names of LLC members/managers
4. Pay filing fee online.
5. Await confirmation. Save the registration certificate to `/home/opc/wholesale/compliance/llc_registrations/`.

**Priority order (by deal volume potential):**
GA → TX → FL → TN → AZ → MO → CA. Skip NC.

---

## 3. E&O Insurance (Errors & Omissions)

**Cost:** $400-$1,500/year for a wholesaler's typical policy.
**Time:** 1 hour to get 3 quotes online.
**Why:** Some title companies require E&O before they'll close with you. Also covers you against misrepresentation claims (the "you said the ARV was X but it was Y" lawsuit risk).

**Free quote sources (no broker, no upsell):**

1. **Hiscox** -- https://www.hiscox.com -- direct online quotes for "Real Estate Services". Plug in: revenue ~$0-$50K, business activity = "real estate wholesaler / investor", years in business = 1.
2. **Next Insurance** -- https://www.nextinsurance.com -- cheaper options for solopreneurs, ~$30/mo for E&O + GL combined.
3. **Thimble** -- https://www.thimble.com -- per-month or per-day insurance, useful when you want to test before committing.
4. **CoverWallet** -- https://www.coverwallet.com -- broker that compares 5+ carriers at once.

**What to ask for in coverage:**

- $1M aggregate limit per claim ($1M total per policy year)
- Specific coverage for "real estate wholesaling" or "contract assignment" -- some policies exclude wholesaling explicitly
- Defense costs INSIDE the limit vs OUTSIDE (outside is better, but pricier)
- Retroactive date as far back as possible (covers claims arising from past acts)

**Cheapest route until first close:** Next Insurance monthly E&O ~$25-40/mo. Cancellable any time. Start with this; upgrade once you have 1-2 closes.

---

## 4. General Liability Insurance

**Cost:** $200-$600/year
**Time:** Bundle with E&O quote above.
**Why:** Covers slip-and-fall on a property you have under contract, marketing-related claims, and other generic liability.

Use the same E&O quote sources above and ask to bundle. Hiscox + Next both offer combined GL+E&O packages cheaper than buying separately.

---

## 5. Bank Reconciliation (Monthly + CPA Quarterly)

**Cost:** $0 if DIY in QuickBooks Online ($30/mo) or Wave (free); CPA quarterly review ~$300-$500/qtr.
**Time:** 30 minutes/month for DIY recon.
**Why:** Audit-required. Discrepancies between bank balance and books are how fraud (or honest mistakes) compound undetected.

**Free DIY workflow:**

1. Open https://www.waveapps.com -- free accounting + bank linking
2. Connect your business checking (Chase, Mercury, Bluevine, whatever you use)
3. Categorize each transaction: assignment fee, marketing, software, EMD held, etc.
4. End of month: confirm bank balance matches Wave balance to the penny
5. Export P&L + Cash Flow report each quarter, save to `/home/opc/wholesale/finance/quarterly_pnl/`

**When to upgrade to CPA:** After first 3 closes OR after first $30K in revenue, whichever first. Use Bench.co ($299/mo) or a local CPA.

---

## 6. Annual External Review (CPA + Attorney + Title Co)

**Cost:** ~$500-$1,500 total per year for a focused 1-hour review with each.
**Time:** 3 hours over the calendar year.
**Why:** External eyes catch what internal audits miss. Title companies are especially valuable -- they see hundreds of wholesale files per year and know where you're cutting corners.

**Schedule (annual, recurring):**

- Q4 each year: 1-hour review with real estate attorney → review contract templates, recent assignment paperwork, any seller complaints
- Q1 each year: 1-hour review with CPA → reconcile annual P&L, tax filing prep, depreciation strategy on any held properties
- Q2 each year: coffee with your primary title-co contact → ask "what's the dumbest thing wholesalers in our market are doing?"

**Calendar reminder pre-set:**

```
0 9 1 10 * /usr/bin/python3 -c "import sys; sys.path.insert(0, '/home/opc/content_tools'); from branded_slack import post_branded_slack; post_branded_slack(channel='#war-room', title='Annual external review reminder', summary='Q4: schedule 1hr attorney review of contracts and consent records.', body='Specific files to bring: PSA template + 3 most recent assignments + ConsentLedger CSV export.', agent_name='Marcus Cole', agent_title='Chief Operator', category='ops')"
```

---

## 7. Testimonials / Case Studies

**Cost:** Free.
**Time:** 15 minutes per testimonial after first 1-3 closes.
**Why:** Social proof is the highest-converting element on a real estate wholesaler's website. One real testimonial beats 10 paragraphs of "we're trustworthy."

**Workflow (after each close):**

1. Within 7 days of closing, send a 2-line follow-up email to the seller: *"Thanks for trusting us with the sale of [address]. If you have a minute, I'd love a quick line about how the process went -- one or two sentences is plenty. With your permission, I might publish it on our site (anonymized if you prefer)."*
2. If they respond positively, ask: *"Mind if I quote you with first name + neighborhood? Or would you prefer 'satisfied seller in Atlanta'?"*
3. Save to `/home/opc/wholesale/marketing/testimonials/`. Format: one .md file per testimonial with date + permission level.
4. Cycle into landing page + Google Business Profile reviews quarterly.

**Compliance note:** Federal Trade Commission requires testimonials reflect typical experience. Don't cherry-pick the highest-money close as "typical" -- if asked, you have to disclose what most sellers actually got.

---

## How to use this guide

1. **Print or open this on your phone**
2. **Block 4 hours over the next 2 weeks** to knock out items 1, 3, 4, and start 2
3. **Items 5 and 6 are recurring** -- set the cron + reminders, then forget
4. **Item 7 waits** for first close (so 30-90 days out)

Once items 1-4 are complete, the audit score should jump from 55% to ~75%. Combined with first close + first testimonial, you're at ~85% -- that's the level a peer wholesaler, title co, attorney, or seller looks at and says "this is a real, professional operation."
