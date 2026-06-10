# VA Hiring Kit -- Wholesale Phone-Callback Specialist

**Goal:** Hire a Filipino virtual assistant from Onlinejobs.ph who handles phone-callback follow-up for the wholesale pipeline. Cost: $4-6/hour, ~20 hours/week = $400-500/month.

**Why a VA, not a bot:** Per TCPA and recent state laws (TX SB 140, NC HB 797), bots cannot make cold or warm phone calls without prior consent. Replies from email-touched leads are treated as warm but not consented for AI. Human VAs are the legally clean and most-effective path.

---

## Job Posting (Onlinejobs.ph)

**Title:** Real Estate Acquisitions Caller -- Wholesale (US-based investor team)

**Schedule:** Mon-Sat, 9 AM - 1 PM Eastern Time (10 PM - 2 AM Philippines time). Flexible.

**Pay:** $5/hour USD ($800/month at 40 hrs/wk). Paid weekly via Wise or Payoneer. Performance bonuses on closed deals: $25/contract signed, $100/property closed.

**Description:**
> We are a US-based real estate wholesale operation covering Cleveland, Atlanta, Dallas, and Jacksonville markets. We need a phone-callback specialist who calls property owners (sellers) and cash buyers who have already responded to our email outreach.
>
> This is NOT cold calling -- every contact has already replied to us by email. Your job is to listen, ask qualifying questions, and either set a follow-up call with our acquisitions manager or take basic property details. Soft, conversational, no high-pressure pitching.
>
> All calls happen through our dialer (we provide a US number). All contact data and talking points are pre-loaded in our dashboard before each call.

**Required:**
- Excellent spoken English, neutral or American accent strongly preferred
- 1+ year of US-based phone work (real estate, customer service, telemarketing)
- Reliable internet, quiet workspace, USB headset
- Available to start within 7 days
- Comfortable with US business norms and addresses

**Bonus:**
- Prior experience with PropStream, BatchLeads, BiggerPockets, or any RE CRM
- Has called for a US wholesaler or fix-and-flip investor before
- Experience with Mojo Dialer, Kixie, or similar
- Spanish bilingual

**To apply:**
1. Record a 60-second voice memo: introduce yourself, describe your strongest US phone job, and explain what you'd say to a homeowner who replied "I might consider selling 123 Main St."
2. Send your resume/profile.
3. Tell us your earliest start date.

We respond within 48 hours to qualified candidates.

---

## Screening Rubric (use during interview)

Score each on 1-5. Hire only candidates scoring 4+ on accent and 3+ on every other.

| Trait | What to listen for |
|---|---|
| Accent / clarity | Can you understand them in 5 seconds? Will an Ohio retiree understand them? |
| Conversational warmth | Do they sound like a person, not a script reader? Empathy on the voice memo? |
| Coachability | Ask them to redo the voice memo with 1 specific change. Did they do it well? |
| Curiosity | Do they ask questions about the role or just answer ours? |
| Reliability indicators | Stable past employment? On-time for the interview? Internet stable on the call? |
| Closing instinct | When you push back ("I don't really want to sell"), do they probe or fold? |

**Red flags:** answering with rehearsed scripts, talking over you, no questions about pay/schedule, can't explain a recent past role concretely.

---

## Onboarding Checklist (first week)

**Day 1 (2 hours):**
- Sign 1099 contractor agreement (PandaDoc) and NDA
- Pay $50 trial payment to confirm payment rail works
- Walk through our 4 markets: typical price points, neighborhood styles, who we buy from
- Review our compliance gates (state_gates.json): which states they CANNOT cold call, when they can
- Set up dashboard login (read-only at first)
- Issue a US virtual phone number via Google Voice / OpenPhone

**Day 2-3 (4 hours):**
- Shadow 5 real callbacks with you (or recordings)
- Practice the seller-callback script (see SELLER_SCRIPT below)
- Practice the buyer-callback script
- 5 mock calls with you playing the seller

**Day 4-7 (20 hours):**
- Live calls supervised: you listen on every 3rd call
- Daily 10-min wrap-up: what worked, what didn't
- Friday: review all dispositions, calibrate notes quality

**Week 2+:**
- Solo calls
- Daily disposition review
- Weekly KPI review: dials, contacts, qualified, set-for-callback, contract-pending

---

## Seller Callback Script (for VA)

**Opening (under 30 seconds):**
> "Hi {{first_name}}, this is {{va_name}} calling back from Everlight Ventures -- you replied to our email about {{property_address}}. Is now an okay time for 5 minutes?"

**If yes:**
1. "Just so I'm not wasting your time -- are you open to selling, or just curious what we'd offer?"
2. If open to selling, ask the 5 qualifiers:
   - **Condition:** "How would you describe the condition? Move-in ready, needs cosmetic, needs major work?"
   - **Occupancy:** "Is it occupied, vacant, or rented?"
   - **Timeline:** "If you got a fair cash offer, how soon would you want to close?"
   - **Reason:** "What's making you consider selling now?"
   - **Number:** "What number would have to be on the table for you to say yes?"
3. "Got it. Let me share these details with our acquisitions lead. They'll call you back within 24 hours with a number. What's the best time tomorrow?"

**If they're cold or hostile:** "Totally fair. We won't bother you again. If anything changes, the email's still in your inbox."

**ALWAYS log:** condition, occupancy, timeline, motivation, asking price they mentioned, mood (motivated/neutral/resistant), commitments, follow-up date.

---

## Buyer Callback Script (for VA)

**Opening:**
> "Hi {{first_name}}, this is {{va_name}} from Everlight Ventures -- you'd reached out about cash deals in {{city}}. Got 3 minutes?"

**Qualify:**
1. "What markets are you actively buying in right now?"
2. "What property types -- SFR, multi, anything land?"
3. "What's your typical price range and rehab budget?"
4. "How fast can you close? Are you cash or hard money?"
5. "Are you flipping or holding?"
6. "How many deals have you closed in the last 12 months?"

**Close:**
> "Perfect. We'll add you to the list and the next time something matches your criteria, you'll get the address, photos, MAO, and a 24-hour window to make an offer. Sound good?"

**ALWAYS log:** markets, property types, price range, rehab budget, close speed, last-12-month deals, proof of funds yes/no.

---

## KPI Targets (for VA performance review)

| Metric | Week 2 | Week 4 | Week 8 |
|---|---|---|---|
| Dials per hour | 8-12 | 10-15 | 12-18 |
| Contact rate | 25% | 30% | 35% |
| Qualifying rate (of contacts) | 40% | 50% | 55% |
| Callback set rate (of qualified) | 30% | 40% | 50% |
| Contracts pending in pipeline (cumulative) | 0 | 1 | 3 |

---

## Tools and Access to Provide

- Dashboard login (broker_ops/callbacks/) -- read+write on CallbackTask only
- Virtual US phone number (Google Voice or OpenPhone, Cleveland 216 or Atlanta 404 area code)
- Headset (they provide; reimburse up to $40)
- Slack invite to #ft-hunters channel for daily standup
- Compliance brief: state_gates.json walkthrough on day 1

---

## Where to post the job

Primary: https://www.onlinejobs.ph/jobseekers/jobs (post under "Customer Service / Sales")
Backup: https://www.upwork.com (more expensive, $8-15/hr range)
Also: REI WEALTH ACADEMY Slack groups, BiggerPockets job board

Expected time-to-hire: 7-10 days from posting to first paid call.

---

_Document maintained by Marcus Cole, Chief Operator. Last updated 2026-04-25._
