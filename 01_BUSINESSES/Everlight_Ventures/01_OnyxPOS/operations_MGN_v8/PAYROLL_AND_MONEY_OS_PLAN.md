# MGN POS -- Payroll, Bookkeeping & Money-OS Plan

_Source: 8-agent deep-research workflow, 2026-06-22. Branch `mgn-pos-restore`. Owner/manager-gated. Decision-grade + cited. Read PART 2 first if you only read one thing._

---

## PART 1 -- DECISION REPORT (payroll + bookkeeping options)

# Payroll + Bookkeeping Inside the POS -- Decision Report for a Single-Location California Nursery + Pet Shop

*Prepared for the owner. Scope: ~5-20 W-2 employees, one CA location, custom Flask POS with a working time clock (clock in/out, CA daily OT 1.5x / 2x double-time, audit-chained punches), a payroll calculator, and per-employee hours CSV export (generic / QuickBooks / Shopify). Goal: legally pay and file CA payroll, kill the QuickBooks friction, and keep the POS time clock as the source of truth.*

---

## 1. The Legal Reality -- "Free + legal payroll" has a catch, and the catch is a line, not a wall

Running payroll is really **two jobs stapled together**, and they have very different legal weight:

**Job A -- Calculate + record (the math and the paperwork).** Take the hours, compute gross, withhold federal income tax, Social Security 6.2%, Medicare 1.45%, **CA Personal Income Tax (PIT)** and **CA State Disability Insurance (SDI) -- 1.3% in 2026 with NO wage cap** (SB 951 removed the ceiling), accrue the employer-side taxes (FUTA, CA UI, ETT 0.1%), print a compliant pay stub, and book the journal entries. **Your POS already does almost all of this**, and doing it in-house is 100% legal.

**Job B -- File + remit + move money (the liability part).** Deposit the federal taxes through **EFTPS**, deposit the CA taxes through **DE 88** on EDD e-Services, file **Form 941** (quarterly) + **940** (annual) + **W-2/W-3** to the SSA, file **CA DE 9 + DE 9C** (quarterly) + **DE 34** new-hire reports, and push net pay into employees' bank accounts via ACH. ([IRS deposit/report rules](https://www.irs.gov/businesses/small-businesses-self-employed/depositing-and-reporting-employment-taxes), [EDD required filings](https://edd.ca.gov/en/payroll_taxes/required_filings_and_due_dates/), [EDD e-file/e-pay mandate](https://edd.ca.gov/en/payroll_taxes/E-file_and_E-pay_Mandate_for_Employers/))

Here is the part most people get wrong, and it flips the whole decision:

> **An employer paying its OWN employees from its OWN bank account is NOT "money transmission" and needs NO special license.** The money-transmitter-licensing "wall" you'll read about (and that the open-source research leaned on) applies to a software *vendor* that receives *other companies'* money to disburse on their behalf. It does not apply to you paying your own staff. California's own regulator confirms it: money transmission requires receiving money *for transmission to another* (Financial Code §2010), and paying a party you already owe -- wages -- falls outside it. ([CA DFPI agent-of-payee opinion](https://dfpi.ca.gov/rules-enforcement/laws-and-regulations/opinion-letters-by-law-subject/receiving-money-for-transmission-and-agent-of-payee-exemption/))

**So the honest bottom line on "free":**

- **Can free / self-hosted software *automate* all of Job B end-to-end? No.** Every open-source tool (ERPNext/Frappe HR, Odoo Community, Akaunting, beancount/hledger/GnuCash, Bigcapital) stops at calculate + record. None files returns, none remits deposits, none originates ACH. ([Frappe maintainers' own US position](https://discuss.frappe.io/t/payroll-not-usable-in-the-united-states/99805))
- **Can a CA employer *legally* run fully-compliant payroll with only free software + free government portals + its own bank? Yes -- it's just manual.** The POS computes gross + the stub + the books; the owner deposits federal tax on free [EFTPS](https://www.irs.gov/payments/eftps-the-electronic-federal-tax-payment-system), deposits CA tax on free [EDD e-Services](https://edd.ca.gov/en/payroll_taxes/file_and_pay/), files 941/940 + DE 9/DE 9C + W-2/W-3 (free, via [IRS e-file](https://www.irs.gov/businesses/e-file-employment-tax-forms) and SSA Business Services Online), and runs direct deposit through the company's own business-bank ACH.

The real choice is therefore **labor + liability, not legality**:

| | Free DIY path | Paid provider path |
|---|---|---|
| Software/fees | $0-pennies (ACH ~$0.26-0.50/txn, or $0 by check) | ~$87-115/mo for ~10 employees |
| Tax tables | **You update them by hand every year** (this is why the abandoned TimeTrex Community Edition is dangerous -- stale tables = wrong withholding = your liability) | Provider keeps them current |
| Deadlines & penalties | **You** carry every EFTPS/DE 88 deadline; late deposits run **2%→15%** penalties | Provider assumes filing/deposit liability (Reporting Agent, Form 8655) |
| Effort | High, recurring, error-prone | Near-zero after setup |

**Two things are non-negotiable on *every* path:**
1. **Workers' comp in force before anyone works** -- Labor Code 3700, required with even ONE employee; no coverage is a misdemeanor with a **≥$10,000** fine. ([CA DWC](https://www.dir.ca.gov/dwc/faqs.html))
2. **EIN + a CA EDD employer payroll-tax account** (register within 15 days of paying >$100 in wages in a quarter). ([EDD registration](https://edd.ca.gov/en/payroll_taxes/employers-payroll-tax-account-registration/))

**Why this matters for the QuickBooks pain specifically:** Effective **July 1, 2026**, QuickBooks Online Payroll makes automated tax withdrawal + filing **mandatory with no opt-out** and pulls the tax money **same-day when you run payroll** -- holding your cash (sometimes weeks before it's due to the agency) in an account that pays *you* nothing. Owners are calling it an "artificial liquidity crisis." That forced cash-flow seizure, plus Intuit's price creep, is exactly the friction the alternatives remove. ([Intuit policy notice](https://quickbooks.intuit.com/learn-support/en-us/employees-and-payroll/updates-to-quickbooks-online-payroll-taxes/00/1606199), [backlash thread](https://quickbooks.intuit.com/learn-support/en-us/taxes/quickbooks-new-horrible-payroll-tax-feature/00/1608063))

---

## 2. Options Matrix

Cost shown for ~10 employees, single CA state. "Files CA+Fed" = remits deposits (EFTPS/DE 88) AND files 941/940/DE 9/DE 9C/W-2.

| Approach | Representative tools | Cost (~10 emp) | Files CA+Fed taxes? | Direct deposit? | API to feed from the POS? | Integration effort | Key pros / cons |
|---|---|---|---|---|---|---|---|
| **Embedded payroll API** | Zeal, Check, Gusto Embedded, Salsa | Not public; ~$35-70/mo base **+ $6-10/emp**, partner keeps ~⅔ -- economics assume **resale at scale** | **Yes**, full CA + federal | Yes | **Yes -- a real write API** (you call "run payroll") | **High** -- must pass a **commercial + security partner review**; 2-4 wks (prebuilt UI) to 3-6 mo (full); you onboard as a "platform" | Pro: payroll truly lives *inside* the POS. Con: **built to resell payroll to many businesses, not for a "platform of one."** Off-profile for a single-FEIN shop with **everyone except possibly [Zeal](https://www.zeal.com/)** ("unlimited workers per FEIN," most tolerant of small). [Gusto Embedded](https://embedded.gusto.com/product/payroll-api) is most mature but the hardest gate. Provider -- not you -- is processor of record. |
| **Full-service direct** | **Gusto, OnPay, Patriot**, SurePayroll, Square | **$87-115/mo** all-in (e.g. Patriot ~$87, Square ~$95, SurePayroll ~$99, [Gusto](https://gusto.com/product/pricing) ~$109, [OnPay](https://onpay.com/payroll/software/costs-pricing/) ~$109) | **Yes**, full CA + federal incl. DE 9/DE 9C, W-2 | Yes | **No open self-serve "run payroll" API for a 10-person shop.** Feed it by **importing the hours CSV** (Gusto's dev API + Embedded sandbox exist but are partner-gated) | **Low** -- CSV import is the integration; live in days | Pro: cheapest path to *fully automated* compliance; friendly UI; assumes the filing liability. Con: payroll lives in the provider's web app, not literally inside the POS. **This is the pragmatic winner.** |
| **Open-source self-host** | ERPNext/Frappe HR, Akaunting, Odoo Community, **Bigcapital**, beancount/hledger | **$0** software (you run the server) | **No** -- calc/record only | **No** ACH origination | Varies (Bigcapital has a REST API; ledgers are file/CLI) | **High** (ERP stack, MariaDB/Postgres, you hand-maintain tax tables) | Pro: own the stack, no SaaS rent, great for the **books**. Con: **does NOT file or pay** -- you still do Job B by hand on free gov portals, and you babysit tax tables. Legal but maximal labor. ([Frappe US gap](https://discuss.frappe.io/t/payroll-not-usable-in-the-united-states/99805)) |
| **Bookkeeping ledger** (pairs with any payroll above) | **Xero, Wave, Zoho Books, Bigcapital (OSS)** | Wave **$0** (Pro $19/mo); [Xero](https://developer.xero.com/pricing) ~$20/mo (Starter API **$0** for your single connection); [Zoho](https://www.zoho.com/us/books/pricing/) Standard ~$20/mo; Bigcapital $0 self-host | N/A (books, not payroll) | N/A | **Yes** -- Xero has the **most mature REST API** + **native Gusto** auto-journal; Wave thinner (GraphQL/REST, no native Gusto); Bigcapital REST + double-entry + inventory on a Node/Postgres stack | Xero **Low**, Wave Low, Bigcapital High | This is the **P&L / general-ledger layer** -- don't rebuild double-entry in Flask, connect to one. [Xero+Gusto](https://www.xero.com/us/legal/terms/xero-gusto-faq/) is the cleanest documented pairing; [Wave](https://www.waveapps.com/pricing) is the free pick. |
| **Fully-manual DIY** | EFTPS + EDD e-Services + SSA BSO + own bank | **$0-pennies** | **Yes -- you do it** | Yes (your bank's ACH) | n/a (you key it) | Recurring manual labor | Legal, $0, no provider needed -- but **you** carry every deadline/penalty and update tax tables yourself. Realistic only if cash is the hard constraint and the owner is disciplined. |

*Unified-API note:* If they ever want ONE API instead of per-vendor CSVs, **[Finch](https://www.tryfinch.com/)** aggregates Gusto/OnPay/Patriot/SurePayroll/etc. -- but it's "assisted" for most small-business connectors, so it doesn't change the near-term answer.

*Avoid for a 10-person shop:* **ADP RUN** (~$150-300/mo, quote-based, term fees), **Paychex Flex** (documented $1,500-$3,000 early-termination fees), **Rippling** (~$250-350/mo, must buy the platform to get payroll), and **Bench** (a bookkeeping *service*, not software; abruptly shut down Dec 2024, restarted under new owners -- no API to your POS). Each is *higher* friction than the QuickBooks they'd replace.

---

## 3. Recommendation -- Three Paths, One Default

### ⭐ DEFAULT -- "Lowest friction, kills the QuickBooks pain" → Gusto + keep the POS time clock + Xero for books

**The stack:**
- **Money + filing engine: Gusto (Simple, ~$109/mo = $49 base + $6/emp).** Calculates, **deposits, and files** all CA + federal taxes (941/940, DE 9/DE 9C, EFTPS/DE 88, W-2/W-3), runs direct deposit. It assumes the filing liability, keeps tax tables current, and has the friendliest UI for a non-accountant owner. ([pricing](https://gusto.com/product/pricing))
- **Source of truth: the POS time clock stays exactly where it is.** Each pay period, an owner/manager-gated screen exports the hours CSV the POS *already* produces → import into Gusto's payroll run. (Gusto's dev API / Embedded sandbox is a *future* upgrade path if you ever want to auto-push hours instead of CSV -- it's the only provider here with a realistic API door.)
- **Books / P&L: Xero (~$20/mo).** Its **native Gusto integration auto-posts every payroll run as a journal entry**, and its mature REST API (Starter tier **$0** for your single connection, and bespoke single-client integrations are exempt from the 2026 API pricing change) lets the POS push **sales** journals. Result: clean double-entry P&L without rebuilding a ledger in Flask. ([Xero+Gusto](https://www.xero.com/us/legal/terms/xero-gusto-faq/), [API pricing](https://developer.xero.com/pricing))

**Why this is the default:** It clears every CA compliance checkbox automatically, removes QuickBooks' forced same-day tax-float and price creep, keeps your strongest asset (the audit-chained time clock + CA OT/DT engine) as the system of record, and the integration is just a CSV the POS already exports plus a documented Gusto→Xero journal sync. Total ~$129/mo, no contracts, live in about a week. *(OnPay ~$109/mo is an equally good swap for Gusto if the owner prefers one flat plan with the best CA EDD-registration hand-holding.)*

### 💵 CHEAPEST COMPLIANT → Patriot Software + Wave (free books)

- **Patriot Software Full Service (~$87/mo = $37 base + $5/emp)** -- cheapest *true* full-service here; files + pays all federal/CA taxes + DE 9/DE 9C + W-2s; US-based support; no setup/cancellation fees; clean CSV hours import. ([pricing](https://www.patriotsoftware.com/pricing/))
- **Wave (Starter, $0)** for the books -- a real P&L and balance sheet a non-accountant can read, free. (Wave even has its own CA-filing payroll at $40/mo + $6/emp if you'd rather single-vendor, but Patriot is cheaper for the filing piece.) ([Wave pricing](https://www.waveapps.com/pricing))
- **All-in ~$87/mo.** Best when the priority is "legally pay people in CA + auto-file DE 9/941 for the least money."
- *Floor case:* the **fully-manual DIY** path (EFTPS + EDD e-Services + SSA BSO + own-bank ACH) is **$0** and legal -- but only choose it if the owner will reliably hit every deposit deadline and update tax tables, because the penalties (2%→15%) land on the owner.

### 🔧 MOST OPEN-SOURCE / DIY → Self-host Bigcapital for the books, POS calculator, owner files manually

- **Bigcapital (AGPL, self-hosted, $0)** for double-entry books + inventory + multi-location on a Node/Postgres stack with a REST API -- the POS pushes sales + payroll journals; the owner only sees reports. ([Bigcapital](https://github.com/bigcapitalhq/bigcapital))
- **POS payroll calculator** stays in-house (already built) for gross + the Labor-Code-226 stub.
- **Owner files + deposits by hand** on the free government portals.
- **Honest caveat:** this is **calc + books only**. It is **legal** but it does **not** file or move money for you, and you must maintain tax tables yourself. Viable *only* because you have a developer (the Hive) in the loop; not an owner-alone option. **If "no SaaS rent" is the real goal, do this for the BOOKS and still pair a paid provider (Gusto/Patriot) for the file-and-pay rail** -- that's the best risk-adjusted version of the DIY dream.

> **Do not** try to make the POS itself the tax filer / money mover for multiple businesses -- that's when you'd need an embedded partner (Zeal) or actual licensing. For Mountain Gardens' own single FEIN, no partner is required; for reselling payroll as a POS feature later, start a Zeal conversation.

---

## 4. Integration Plan Into the POS

**The honest integration truth:** for a 10-person shop, the open "run-payroll" write API is **closed** -- embedded APIs (Zeal/Check/Gusto Embedded) require a partner review, and full-service providers don't expose self-serve payroll writes at this size. **So the connective tissue is the hours CSV the POS already exports**, not a live API. That's a feature, not a limitation: it's lower-risk and ships in days.

**What we BUILD into the POS (owner/manager-gated):**
1. **Payroll Prep screen** -- pulls the period's punches from the existing audit-chained time clock, applies the CA OT 1.5x / DT 2x engine you already have, and generates the **provider-shaped hours CSV** (Gusto/generic format). One button per pay period. This is mostly wiring the *existing* export to a clean, gated UI.
2. **Labor Code 226 stub preview** -- render the 9 required line items (gross, total hours, all deductions, net, pay-period dates, name + last-4 SSN, employer legal name/address, **each hourly rate with hours at that rate** incl. OT/DT bands, plus the **CA paid-sick-leave balance**). The provider produces the *official* stub; this preview lets the manager sanity-check before submitting. ([Labor Code 226](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=LAB&sectionNum=226.), [DLSE sample stub](https://www.dir.ca.gov/dlse/paystub.pdf))
3. **Books push** -- after each run, post two journal entries to the bookkeeping layer: **sales** (from POS) and **payroll** (Gusto pushes this natively to Xero; for Wave/Bigcapital we post via API). Owner sees a live P&L.
4. **Owner/manager gate** -- all of the above lives behind the existing role gate; hourly staff only ever see the clock.

**What the PROVIDER handles (the liability we deliberately do NOT build):**
- Federal **EFTPS** deposits + CA **DE 88** deposits on the correct lookback-driven schedule (monthly vs. semiweekly; the $100k next-day and $350-PIT acceleration triggers).
- **941 / 940 / DE 9 / DE 9C / DE 34 / W-2 / W-3** filing (CA e-file is mandatory; the provider holds the Reporting Agent role via Form 8655).
- **Direct deposit ACH** and keeping withholding tables current (incl. **SDI 1.3% no-cap 2026** and CA min wage **$16.90/hr effective Jan 1, 2026**). ([EDD rates](https://edd.ca.gov/en/payroll_taxes/rates_and_withholding/), [CA min wage](https://www.dir.ca.gov/DIRNews/2025/2025-118.html))

**Data flow (one line):** `POS time clock (source of truth) → hours CSV → Gusto (calc + deposit + file + direct deposit) → payroll journal → Xero/Wave/Bigcapital (P&L)`; the POS separately pushes sales journals to the books.

---

## 5. Phased Rollout

| Phase | What happens | Who | Rough effort |
|---|---|---|---|
| **0 -- Compliance gate (do FIRST, blocks everything)** | Confirm **EIN**, register/verify the **CA EDD** account, and **bind a workers' comp policy** before anyone is paid under the new system. Collect each employee's **W-4 + CA DE 4**; ensure **DE 34** new-hire + **2810.5** wage notices are issued. | Owner (+ our checklist) | 1-3 days, mostly waiting on EDD/carrier |
| **1 -- Stand up the provider** | Open the Gusto (or OnPay/Patriot) account, load employees, bank, and CA tax IDs; run **one parallel test payroll** against the old QuickBooks numbers to confirm withholding (esp. SDI no-cap) ties out. | Owner + dev | 2-4 days; Gusto live in ~a week |
| **2 -- POS → provider CSV** | Build the owner/manager-gated **Payroll Prep screen** that turns the existing punches into the provider's hours CSV; verify OT/DT bands carry over. Cut over: time clock stays SOT, CSV feeds Gusto. | Dev | 3-5 days (wiring existing export + gate) |
| **3 -- 226 stub preview** | Render the 9-item stub preview + sick-leave balance in-POS for manager verification before each submit. | Dev | 2-4 days |
| **4 -- Books layer** | Connect bookkeeping: turn on **native Gusto→Xero** journal sync (or build the Wave/Bigcapital API post); wire the POS **sales** journal push. Owner gets a live P&L. | Dev | 3-6 days (Xero native = fast; OSS = longer) |
| **5 -- Run live + decommission QuickBooks** | Run 1-2 live cycles fully on the new stack, confirm a clean quarterly **DE 9/DE 9C** files through the provider, then drop QuickBooks **before its July 1, 2026 forced-float** bites. | Owner + dev | 1 pay cycle to validate |
| **6 -- (Optional, future) Embedded API** | Only if "payroll literally inside our app" becomes a hard product requirement or a SaaS-resale ambition for the POS: open a **Zeal** partner conversation and replace the CSV with a live write API. | Dev + Zeal review | Weeks-months; commercial + security review |

**Total to a compliant, QuickBooks-free production stack: roughly 2-3 weeks of dev plus the Phase-0 registration lead time** -- with Phase 0 (EIN, EDD account, workers' comp) as the hard prerequisite that must clear before the first real payroll runs.

---

### One-paragraph answer for the owner
Build the *calculator, the compliant pay stub, and the books* into the POS -- that's legal and you've already done most of it -- but **do not** try to build the tax deposits, government filings, and direct deposit into it. Those carry the liability and need either you doing them by hand on free IRS/EDD portals (legal, $0, but you own every deadline) or, the smart move, a ~$87-109/mo full-service provider (**Gusto or Patriot**) that files CA + federal automatically and keeps the tax tables current. Keep the POS time clock as the source of truth, feed the provider the hours CSV you already export, pair it with **Xero** (or free **Wave**) for the P&L, and lock in workers' comp + your EDD account before the first check. That kills the QuickBooks forced-tax-float pain without turning your nursery into a licensed payroll company.

---

## PART 2 -- LEGAL VERDICT (can free/OSS legally pay CA payroll?)

Verified. The provided research has one load-bearing error that flips the answer, and I confirmed it against primary sources. Here is the definitive verdict.

---

# Can a CA small business legally run W-2 payroll on only free / self-hosted software, no licensed provider?

## The question is really two questions, and they have opposite answers

**Q1 -- Can free/open-source software AUTOMATE the whole thing (calculate + deposit + file + direct-deposit) end-to-end, by itself?**
**No.** Every OSS tool (ERPNext/Frappe HR, Odoo Community, Akaunting, beancount/hledger/GnuCash) stops at *calculate + record*. None files 941/940/DE9/DE9C, none remits EFTPS/DE88 deposits, none originates ACH. The provided OSS research is correct on that point.

**Q2 -- Can a California employer LEGALLY run fully-compliant W-2 payroll using ONLY free software + free government portals + its own bank, with no licensed payroll provider?**
**Yes -- unambiguously legal.** It is just *manual*, not *automated*. No licensed payroll provider is legally required. The owner does the deposits, filings, and direct deposit themselves through free channels.

The OSS write-up blurs these two by invoking a "money-transmitter licensing wall." That wall is real for a software *vendor* reselling payroll to *other* businesses -- it does **not** apply to an employer paying its **own** employees. That is the error that, once corrected, makes self-hosted-DIY payroll fully legal.

---

## Why the "money-transmitter wall" does NOT bind the employer

The varkrz/CSBS sources the OSS research cites describe **third-party payroll processors** that *receive other companies' money* to disburse wages and remit taxes on their behalf. That's the activity that can trigger money-transmitter licensing.

An **employer paying its own staff from its own funds is not money transmission at all** -- there is no "receiving money from one person to deliver to another." California's regulator confirms the framework: under Financial Code §2010, money transmission requires receiving money *for transmission to another*, and obligations satisfied by paying a party you already owe (the agent-of-payee / wage scenario) fall outside it ([DFPI opinion letter](https://dfpi.ca.gov/rules-enforcement/laws-and-regulations/opinion-letters-by-law-subject/receiving-money-for-transmission-and-agent-of-payee-exemption/)). And even for *third-party* payroll processors, California expressly **exempts** them from MTL ([CSBS/NPRC, p. cited](https://www.csbs.org/sites/default/files/2019-04/NPRC%20Response%20to%20Request%20for%20Information.pdf)). Either way, the employer-paying-its-own-employees case never reaches the wall.

So: **the employer can move its own payroll money without any license.** The bank is the ACH originator; the employer just signs the bank's ACH origination/terms agreement ([ADP direct-deposit setup](https://www.adp.com/resources/articles-and-insights/articles/h/how-to-setup-direct-deposit.aspx), [Justworks small-biz direct deposit](https://www.justworks.com/blog/beginners-guide-how-to-set-up-direct-deposit-for-small-businesses)). Median ACH cost is ~$0.26-0.50 per transaction ([Nacha](https://www.nacha.org/content/ach-supports-small-businesses)) -- or pay by paper check for $0.

---

## What free software can legally do vs. what the human (or a licensed entity) must do

| Payroll job | Can free/self-hosted SW do it? | Who legally performs it on the DIY path |
|---|---|---|
| Compute gross, fed/FICA/Medicare withholding, CA PIT, **CA SDI 1.3% no-cap**, employer FUTA/UI/ETT | **Yes** (calculator -- ERPNext formulas, Akaunting, or POS engine), *if tables kept current* | The software (owner-maintained) |
| Labor Code 226 itemized 9-item stub w/ OT/DT bands + sick-leave balance | **Yes** -- strongest asset; the POS time clock is the lawful source of truth | The POS / software |
| Post the GL journal entries (bookkeeping) | **Yes** -- beancount/hledger/GnuCash/Akaunting | The software |
| **Deposit federal taxes (EFTPS)** | No | **Owner, FREE** at [eftps.gov](https://www.irs.gov/payments/eftps-the-electronic-federal-tax-payment-system) -- no fee, self-service, no provider |
| **Deposit CA taxes (DE 88)** | No | **Owner, FREE** in [EDD e-Services for Business](https://edd.ca.gov/en/payroll_taxes/file_and_pay/) |
| **File 941 (qtrly) / 940 (annual)** | No | **Owner** -- paper filing is still allowed for both, or free e-file ([IRS e-file employment tax](https://www.irs.gov/businesses/e-file-employment-tax-forms)) |
| **File DE 9 + DE 9C (qtrly), DE 34 new-hire** | No | **Owner, FREE** in EDD e-Services (e-file is mandatory there -- but the portal is free) ([EDD e-file/e-pay mandate](https://edd.ca.gov/en/payroll_taxes/E-file_and_E-pay_Mandate_for_Employers/)) |
| **W-2/W-3 to SSA by Jan 31 (e-file required at 10+ returns)** | No | **Owner, FREE** via SSA Business Services Online (BSO) -- satisfies the 10+ e-file mandate at $0 |
| **Direct deposit (ACH)** | No (no OSS tool originates ACH) | **Owner's own business bank** -- ACH origination agreement; no MTL needed |

So the only three things "no OSS tool does" (file / remit / move money) are each done **free** by the owner through government portals + the company's own bank. None of them legally *requires* a licensed provider, an embedded API, or a money-transmitter license. The embedded-payroll APIs (Check/Zeal/Gusto Embedded/Salsa) and full-service providers (Gusto/OnPay/SurePayroll) are **convenience + liability-transfer purchases, not legal prerequisites** -- and per your own research, all the embedded APIs are off-profile for a single-FEIN shop anyway.

---

## The real tradeoff (this is what the owner is actually choosing between)

It is **labor + liability**, not legality:

- **Free DIY path:** $0 software + ~$0-pennies ACH. But the owner personally carries every deadline and every penalty -- late EFTPS deposits run **2%→15%** penalties, blown withholding, missed DE 9C. And the owner must **hand-update tax tables every year** (this is exactly why TimeTrex Community going stale in Oct 2024 is dangerous -- wrong tables = wrong withholding = the owner's liability).
- **Provider/Reporting-Agent path (Form 8655):** ~$40/mo + ~$6-10/employee. The provider assumes filing/deposit liability and keeps tables current. That's what the money buys -- not legality, indemnity and automation.

Two things are non-negotiable regardless of path: **workers' comp before anyone works** (Labor Code 3700, 1+ employee, ≥$10k fine + misdemeanor) and an **EIN + EDD account**.

**For the POS *product* being built:** building the calculator + the 226-compliant stub + the books *inside the POS for Mountain Gardens' own FEIN* is fully legal. The line you'd cross is building an automated *file-and-pay-and-ACH* engine that serves *other* businesses as a SaaS -- that's when you'd need an embedded-payroll partner (Zeal) or licensing. For one shop's own payroll, no partner is required.

---

**VERDICT:** Yes -- a California nursery can legally run fully-compliant W-2 payroll (correct withholding incl. SDI 1.3% no-cap, federal + CA deposits, all quarterly/annual filings, and direct deposit) using only free/self-hosted software with **no licensed payroll provider**, because an employer paying its own employees is not "money transmission" and every government channel it needs is free and self-service: the POS/OSS tool computes gross + the Labor-Code-226 stub + the books, the owner deposits federal tax on EFTPS and CA tax on EDD e-Services (both free), files 941/940 (paper or free e-file) + DE 9/DE 9C + W-2/W-3 (free SSA BSO), and originates direct deposit through the company's own business-bank ACH (or pays by check). What free software *cannot* do is *automate* those last three steps -- so the honest choice is **free-but-fully-manual DIY** vs. **paid-but-automated provider that also absorbs the penalty/liability and keeps tax tables current** -- a cost-and-risk decision, not a legality wall; just make sure workers' comp is in force before anyone clocks in.

---

## PART 3 -- "MONEY OS" ENGINE SPEC (the profit/payday/bill layer to build on the POS)

# Mountain Gardens POS -- "Money OS" Layer -- Feature Spec

_Owner/manager-gated financial cockpit built ON TOP of the existing Flask + CSV POS (`operations_MGN_v8`: `MGN_APP.py` routes + `POS_CORE.py` data layer, port 5000, CSV-backed). The POS sales logs and the tamper-evident time clock stay the single source of truth. Nothing in this layer rings sales, edits punches, or moves money on its own -- it reads the existing ledgers, computes the money picture, and stages actions behind owner approval._

---

## 0. Architecture fit (how it bolts on)

**Gating.** Every route below is decorated with the existing `@manager_required` (`MGN_APP.py:122`, allows `Manager/Owner/Admin`). Add a finer `@owner_required` for money-movement endpoints (fund payroll, toggle autopilot, edit allocation rules) -- gate on `session["role"] == "Owner"`.

**New code, no rewrites.**
- New engine module `money_core.py` (mirrors `POS_CORE.py` conventions: `read_csv`/`write_csv`/`append_csv`, `ensure_csv`, the `_IO_LOCK`, atomic temp→fsync→rename writes, CSV-injection guard already used in `tools/inventory_transfer.py`).
- New route blueprint section in `MGN_APP.py` under `/money/*` + `/api/money/*`.
- New data dir `Money_OS/` alongside `Payroll/`, `Till/`, `Daily_Reports/`.
- New dashboard `templates/money/*.html`; one nav tile on the owner dashboard (`/dashboard/owner`, `MGN_APP.py:2534`).

**Reuses these existing functions (do not duplicate):**
| Need | Existing function | File |
|---|---|---|
| Daily revenue / COGS / gross profit / margin / payment + category breakdown | `_compute_daily_sales_metrics(rows)` | `MGN_APP.py:7889` |
| Load a day's sale lines | `_load_saleslog_rows` + `_find_saleslog_file_for_date`, or `get_sales_for_date(d)` | `MGN_APP.py` / `POS_CORE.py:1492` |
| Per-day labor (hours × rate) | `_get_labor_for_date_stub(base_dir, date_str)` | `MGN_APP.py:8018` |
| **CA daily OT/DT split** | `calculate_california_hours(punches)` + `scan_timeclock_files(start,end)` | `MGN_APP.py:6247 / 6204` |
| Period hours from clock | `calculate_hours_for_period(emp, start, end)` | `POS_CORE.py:2558` |
| Full payroll calc (gross/taxes/net) | `calculate_payroll` / `run_payroll` | `POS_CORE.py:2629 / 2752` |
| Pay rate / config | `get_employee_pay_rate`, `get_employee_pay_config`, `get_pay_period` | `POS_CORE.py` |
| Till cash events | `Till/ledger.csv`, `Till/till_state.csv` | `Till/` |

**New CSV/ledger files (all in `Money_OS/`, headers `ensure_csv`'d on first read):**
- `Overhead.csv` -- recurring fixed costs: `Bill_ID,Vendor,Category,Amount,Frequency,Due_Day,Autopay,Account,Active,Notes` (Frequency ∈ WEEKLY/MONTHLY/QUARTERLY/ANNUAL).
- `Bills.csv` -- concrete bill + vendor-order instances: `Bill_ID,Vendor,Type,Amount,Due_Date,Status,Priority,Source,Approved_By,Approved_At,Paid_At,Notes` (Type ∈ BILL/ORDER; Status ∈ SCHEDULED/APPROVED/PAID/SKIPPED).
- `Envelopes.csv` -- running balances: `Envelope,Balance,Target,Updated_At` (Envelope ∈ PAYROLL/PAYROLL_TAX/SALES_TAX/BILLS/RESERVE/OWNER).
- `Envelope_Ledger.csv` -- every set-aside/withdraw: `Entry_ID,Date,Time,Envelope,Direction,Amount,Source,Ref,Note` (append-only, fsync'd).
- `Allocation_Rules.csv` -- `Rule_ID,Trigger,Condition,Envelope,Percent_Of,Percent,Active`.
- `PnL_Daily.csv` -- cached daily snapshot: `Date,Revenue,COGS,Gross_Profit,Labor_Cost,Overhead_Allocated,Net_Profit,Margin_Pct,Flag`.
- `Cash_Snapshots.csv` -- bank balance pulls: `Date,Time,Source,Account,Balance,Note` (Source ∈ PLAID/MANUAL).
- `Payroll_Funding.csv` -- readiness history: `Period_ID,As_Of,Accrued_To_Date,Employer_Tax_Est,Projected_To_Payday,Cash_On_Hand,Payroll_Envelope,Gap,Alert_Level`.
- `Money_Settings.csv` -- single-row config: thresholds, employer tax burden %, autopilot flags, Plaid on/off.

---

## 1. DAILY / WEEKLY P&L

**Goal:** one screen that turns the day (and week) into a profit number, sourced from sales truth + time-clock truth, and flags whether the day paid for itself.

**Route:** `GET /money/pnl?date=YYYY-MM-DD&range=day|week` → `templates/money/pnl.html`; data also at `GET /api/money/pnl`.

**Engine:** `money_core.compute_daily_pnl(d)`:
1. **Revenue / COGS / gross profit / margin** -- call `_compute_daily_sales_metrics(get_sales_for_date(d))`. Revenue uses `Line_Total` (the inflated-`Subtotal` bug was already fixed). COGS = Σ `COGS_Line`; gross profit = revenue − COGS. (All four already returned.)
2. **Labor cost (OT-correct)** -- do **not** reuse `_get_labor_for_date_stub` for the money number: it multiplies a flat rate × hours and omits the OT premium. Add `compute_labor_cost_for_date(d)`:
   - pull the day's punches (`get_punches_for_date(d)`), group by employee, run `calculate_california_hours(...)` to get `regular / overtime / doubletime` hours,
   - `labor = Σ (reg×rate + ot×rate×1.5 + dt×rate×2)` using `get_employee_pay_rate(emp)`,
   - add an **employer payroll-tax burden** line (≈ `EMPLOYER_TAX_BURDEN_PCT`, default 0.12 of wages -- SS 6.2% + Medicare 1.45% + FUTA + CA UI/ETT; exact figure replaced by the provider's number once connected, §5). True cost of an hour ≠ the wage.
3. **Overhead (prorated)** -- `overhead_allocated = daily_share(Overhead.csv)`: monthly→÷30.44, weekly→÷7, quarterly→÷91.3, annual→÷365, summed. Open days only if owner sets an "open-days/week" divisor in `Money_Settings`.
4. **Net profit** = gross profit − labor − overhead_allocated. (Extends the existing `/reports/daily` math, which already does `net_profit = gross_profit − total_payroll`; Money OS adds overhead and OT-correct labor.)
5. **Flag** -- `flag_day()`: compare net profit and margin to a trailing-28-day average of `PnL_Daily.csv`. `PROFITABLE` (≥ avg), `SLOW` (positive but < 60% of avg, or below `slow_threshold`), `LOSS` (net < 0). Color the day green/amber/red.

**Weekly:** `compute_weekly_pnl(week_start)` sums Mon-Sun of `PnL_Daily.csv` (matching the existing `Sales_Logs/YYYY/MM/Week_N/` bucketing), plus a 7-day prorate of overhead. Shows best/worst day, day-of-week profitability heat row ("Sundays lose money").

**Caching:** on EOD close (the existing `/api/till/close` path that already writes `Daily_Reports/<date>/`), also write the day's row to `PnL_Daily.csv`. Re-render lazily for any back-date.

**Reads:** `Sales_Logs/*` (revenue, COGS), `Time_Clock/*` (labor via CA OT), `Payroll/Employee_Pay_Config.csv` (rates), `Money_OS/Overhead.csv`.

---

## 2. PAYROLL READINESS TRACKER

**Goal:** answer "do I have the cash to make payroll, and how much do I owe by Friday?" -- including the owner's real case: _haven't run payroll in a while → here's the catch-up._

**Route:** `GET /money/payroll-readiness` → `templates/money/readiness.html`; `GET /api/money/payroll-readiness`.

**Engine `money_core.payroll_readiness()`:**
1. **Accrued-to-date (owed now)** -- for the **current OPEN period** (`Pay_Periods.csv`, Status=OPEN), sum OT-correct gross wages for every worked day from `Start_Date`→today using `calculate_california_hours` per employee (same engine as §1, but gross wage not loaded cost). Add salaried accrual = `salary / periods_per_year × (days_elapsed / period_days)`.
2. **Catch-up case (the key one)** -- scan `Pay_Periods.csv` for **all** periods with Status=OPEN whose `End_Date` ≤ today and **no matching rows in `YYYY_Payroll_Runs.csv`** (= never run). Sum their gross. Output: _"3 pay periods unfunded since 5/15 → catch-up wages owed: $X (+ ~$Y employer tax)."_ This is unfunded-back-pay, surfaced loudly at the top.
3. **Projected-to-next-payday** -- accrued + projected remaining: `avg_daily_labor (trailing 14 worked days) × scheduled workdays remaining` to `Pay_Periods.Pay_Date`. Salaried = remaining straight-line.
4. **Employer tax estimate** -- `gross × EMPLOYER_TAX_BURDEN_PCT` (the §5 provider replaces this with exact once live).
5. **Cash-on-hand** -- from `get_cash_on_hand()` (§3 / §last): Plaid balance if connected, else latest `Cash_Snapshots.csv` MANUAL entry, else Till cash + a flagged "card-in-transit" estimate. **Flag clearly when the number is stale or manual.**
6. **Gap + alert** -- `gap = (owed_now + projected + employer_tax) − max(cash_on_hand, PAYROLL+PAYROLL_TAX envelopes)`.
   - Alert copy: _"You owe ~$X in wages + ~$Z employer tax by Fri 6/27. You have $C set aside. Short $G -- set aside $G over the next N days (~$G/N per day)."_
   - Alert_Level: GREEN (covered), AMBER (covered by cash but not by envelopes), RED (gap > 0), BLACK (catch-up back-pay exists).
7. Persist each computation to `Payroll_Funding.csv` for trend + audit.

**Reads:** `Time_Clock/*`, `Payroll/Pay_Periods.csv`, `Payroll/YYYY_Payroll_Runs.csv`, `Payroll/Employee_Pay_Config.csv`, `Money_OS/Envelopes.csv`, `Money_OS/Cash_Snapshots.csv`.
**Needs bank API:** the cash-on-hand half is only real with Plaid (or a fresh manual entry) -- see final section.

---

## 3. FUND ALLOCATION / ENVELOPES

**Goal:** on a good day, auto-route money into buckets so payroll, taxes, and bills are funded before the owner spends the surplus. Envelopes are an **accounting overlay** (running balances + a ledger), not separate bank accounts -- until/unless the owner opens sub-accounts.

**Routes:**
- `GET /money/envelopes` → balances + ledger (`templates/money/envelopes.html`).
- `GET/POST /money/envelopes/rules` (`@owner_required`) → edit `Allocation_Rules.csv`.
- `POST /money/envelopes/allocate` → run today's allocation (also auto-fired on EOD close).
- `POST /money/envelopes/move` (`@owner_required`) → manual transfer between envelopes (audited).

**Default envelopes:** `PAYROLL`, `PAYROLL_TAX`, `SALES_TAX`, `BILLS`, `RESERVE`, `OWNER`.

**Allocation engine `run_daily_allocation(d)`** (idempotent per date -- keyed in `Envelope_Ledger`):
1. Compute the day's `net_profit` (§1) and the day's **sales tax collected** = Σ `Tax_Amount` from `Sales_Logs` (this is exact, logged per line at 8.25%).
2. **Always** sweep that day's collected sales tax into `SALES_TAX` (it isn't the store's money -- it belongs to CDTFA). This alone makes the quarterly CDTFA return self-funded.
3. If `net_profit > 0`, apply `Allocation_Rules.csv` in order. Default good-day ruleset (owner-editable):
   - PAYROLL ← 30% of net profit
   - PAYROLL_TAX ← 8% of net profit
   - BILLS ← 15% of net profit
   - RESERVE ← 10% of net profit
   - OWNER ← remainder
   - On a `SLOW`/`LOSS` day: skip discretionary envelopes, still bank sales tax + a reduced payroll set-aside.
4. Each move writes an `Envelope_Ledger` row (Direction=IN, Source=`daily_allocation`, Ref=date) and updates `Envelopes.csv` under `_IO_LOCK`.

**Display:** envelope cards with Balance vs Target (Target for PAYROLL/PAYROLL_TAX pulled from §2's projected need → "PAYROLL envelope 72% funded for Friday"). Ledger table = every set-aside and every draw, fully auditable.

**Reads:** `PnL_Daily.csv` / live §1, `Sales_Logs/*` (Tax_Amount), `Money_OS/Allocation_Rules.csv`. **Writes:** `Envelopes.csv`, `Envelope_Ledger.csv`.

---

## 4. BILLS + ORDERING (with autopilot + approval gates)

**Goal:** a weekly "what to pay and order" priority list driven by cash + the next payday, with an optional "let it run" mode that **still never moves money without owner approval** unless the owner explicitly arms an item.

**Routes:**
- `GET /money/bills` → priority view (`templates/money/bills.html`).
- `POST /money/bills/add` → one-off bill or vendor order into `Bills.csv`.
- `GET/POST /money/bills/recurring` → manage `Overhead.csv` (rent, utilities, insurance, software, vendor standing orders).
- `POST /money/bills/<id>/approve` (`@owner_required`) → flip SCHEDULED→APPROVED (records `Approved_By/At`).
- `POST /money/bills/<id>/pay` (`@owner_required`) → mark PAID (records `Paid_At`); if an external pay rail is wired, this is the only place it fires.
- `POST /money/autopilot` (`@owner_required`) → toggle autopilot + per-category arm flags in `Money_Settings.csv`.

**Bill generation:** a daily pass (`generate_due_bills()`, run on first load each day) materializes the next instance of each `Overhead.csv` row into `Bills.csv` as `SCHEDULED` when its `Due_Day` is within a 14-day window -- so recurring rent/utilities show up automatically.

**Priority engine `bill_priority_view(week)`:**
- Inputs: open `Bills.csv` (SCHEDULED/APPROVED), `BILLS` envelope balance, cash-on-hand (§3/last), next `Pay_Date` and payroll need (§2).
- **Payroll is always priority 0** -- bills are ranked only against cash _after_ reserving the payroll + tax envelopes. The view literally shows: _"Available after payroll reserve: $A."_
- Rank remaining bills by: overdue first, then due-this-week, then priority field, then size. Each row tagged **PAY NOW / OK TO PAY / WAIT (short cash) / AFTER PAYDAY**.
- Vendor **orders** (Type=ORDER) ranked separately, can be linked to low-stock signals from the existing `get_reorder_recommendations()` (`POS_CORE.py:1199`) so "what to reorder" is data-driven.

**Autopilot with gates (`Money_Settings`):**
- `autopilot_mode ∈ OFF | SUGGEST | ARMED`.
- **OFF/SUGGEST (default):** the system schedules, prioritizes, and drafts everything; a human clicks Approve to pay. Nothing leaves an account without `@owner_required` approval. This is the doctrine-compliant default ("nothing moves money without owner approval").
- **ARMED:** only categories the owner explicitly flips to `autopay=Y` in `Overhead.csv` **and** under a per-transaction `auto_pay_ceiling` (e.g., $500) can auto-mark-pay on due date -- and even then it posts a notification + a 24h reversible "armed" hold, logged to `Envelope_Ledger` + an audit line. Payroll funding is **never** auto-armed; it always requires the §5 approval click.
- Every autopilot action writes a tamper-evident audit line (reuse `append_audit_event` from the existing time-clock chain pattern, `POS_CORE.py`).

**Reads:** `Money_OS/Overhead.csv`, `Bills.csv`, `Envelopes.csv`, `Inventory` reorder recs. **Cash check** needs the bank API for "real available."

---

## 5. TIE-IN TO THE PAYROLL PROVIDER (fund → schedule → post to books)

**Principle:** the POS time clock is the system of record for **hours**; the chosen full-service payroll provider is the system of record for **tax filing + money movement** (direct deposit, employer tax remittance, CA EDD + federal filings, W-2s). Money OS is the bridge: it pushes hours, funds the run, and writes the result back to the books. This is what gets the owner off QuickBooks friction while staying CA-compliant.

**Provider adapter (`money_core/payroll_provider.py`)** -- a thin interface so the chosen provider from the research drops in without touching the rest:
```
class PayrollProvider:
    def push_hours(period_id, hours_by_employee)   # reg/OT/DT/PTO/sick per employee
    def preview_run(period_id) -> {gross, employee_tax, employer_tax, net, debit_total, pay_date}
    def submit_run(period_id, approved_by)         # gated; debits operating acct, schedules deposits
    def get_run_status(run_id)                     # POLL or webhook
    def list_filings(period)                       # CA DE-9/DE-9C, 941, etc.
```
Primary target = a full-service API provider that **files CA payroll taxes automatically** (Gusto-class: direct deposit + UI/ETT/SDI + DE-9/DE-9C + federal 941/940 + year-end W-2). Documented alternates behind the same interface: an embedded-payroll API (Check) or Square Payroll. The exact pick is whatever the generic research selected; only this adapter file changes.

**Flow:**
1. **Hours push.** When the owner opens a pay period for processing, `push_hours()` sends per-employee `reg/OT/DT/PTO/sick` straight from `calculate_california_hours` over `scan_timeclock_files(start,end)` (the same numbers behind §1/§2). The existing `GET /payroll/export-hours?format=generic|quickbooks|shopify` (`MGN_APP.py:6724`) gains a `format=provider` that emits the adapter's payload -- reusing code that already exists. The POS clock stays truth; the provider never originates hours.
2. **Fund.** `GET /money/payroll/fund` shows the provider's `preview_run` (gross, employee + employer tax, total debit, deposit date) **next to** the §2 readiness + §3 PAYROLL/PAYROLL_TAX envelope balances and §-last cash-on-hand. If the envelope/cash can't cover `debit_total`, the page blocks submit and shows the §2 set-aside plan. `POST /money/payroll/fund` (`@owner_required`) is the only thing that calls `submit_run()` -- explicit owner approval, audited.
3. **Schedule payday.** `pay_date` comes from `Pay_Periods.csv`; the provider schedules the deposit. A reminder is created on the calendar via the existing branded calendar/notification path.
4. **Post the run to the books.** On `submit_run` success (or provider webhook `POST /money/provider/webhook`):
   - Write per-employee rows into `Payroll/YYYY_Payroll_Runs.csv` (existing schema) and flip the period to PROCESSED -- honoring the **existing payroll-run lock** (`/payroll/run` refuses a re-run of a PROCESSED period unless `force=1`, audit-logged) so the provider callback can't double-post.
   - Draw `PAYROLL` and `PAYROLL_TAX` envelopes down by the funded amounts (`Envelope_Ledger` Direction=OUT, Source=`payroll_fund`).
   - Append a tamper-evident `payroll_funded` audit line (same chain as the time clock).
   - Drop a `Bills.csv` PAID row for the provider debit so it shows in cash flow.
   - Store provider `run_id` + filing references in the run's `Notes` for the §1 books and year-end.

**Reads:** `Time_Clock/*`, `Pay_Periods.csv`, `Employee_Pay_Config.csv`, `Envelopes.csv`. **Writes:** `YYYY_Payroll_Runs.csv`, `Envelope_Ledger.csv`, `Bills.csv`, audit chain. **External:** the chosen provider's API for the actual money + tax filing.

---

## Cross-cutting: real cash-on-hand (where a bank API is required)

Several pieces above (§2 gap, §4 "available after payroll," §5 fund check) need **true cash, not drawer cash**. The POS only knows cash in the `Till/ledger.csv` drawer; card sales settle to the bank 1-2 days later, and bills/payroll debit the bank, not the till. So:

- **`get_cash_on_hand()` resolution order:**
  1. **Plaid** (`/accounts/balance/get`) on the operating checking account → freshest real balance. This is the only fully-real source. Store each pull in `Cash_Snapshots.csv` (Source=PLAID).
  2. **Manual** -- `POST /money/cash/manual` lets the owner type today's bank balance (Source=MANUAL); the UI flags it with an "as of" timestamp and goes stale after 24h.
  3. **Derived fallback (clearly labeled "estimate")** -- last known bank balance + cleared card settlements + till cash − scheduled debits. Used only when neither Plaid nor a fresh manual entry exists.
- **Day-one without Plaid:** everything ships and works on the **manual** path (owner enters balance), so the build isn't blocked on a banking integration. Plaid is the upgrade that makes cash-on-hand automatic and the §2 alerts trustworthy without daily data entry.
- Keep Plaid keys in `.env` (same pattern as `SMTP_*` / `MGN_EOD_EMAIL`); bind stays `127.0.0.1` per network doctrine; the Plaid client lives in `money_core` so it's the single egress point.

---

## Build order (each step shippable + testable, mirrors the existing `tools/test_*` discipline)

1. `Money_OS/` scaffolding + headers + `money_core` read/write helpers + `Money_Settings`.
2. **§1 P&L** (highest value, pure-read, reuses existing metrics) + `PnL_Daily.csv` cache on EOD close.
3. **§3 envelopes** + daily allocation (sales-tax sweep first -- it's exact and compliance-critical).
4. **§2 readiness** + catch-up scan + alerts.
5. **§4 bills/ordering** + autopilot gates (SUGGEST default).
6. **§5 provider adapter** + fund flow (last -- depends on the research's provider pick + API keys).
7. `get_cash_on_hand()` manual path throughout; Plaid swapped in when keys land.

Owner sees one new tile -- **Money OS** -- on `/dashboard/owner`: today's profit (green/amber/red), payroll-readiness gap, envelope funding bars, and this week's bills-to-pay. Everything else is one click in.
