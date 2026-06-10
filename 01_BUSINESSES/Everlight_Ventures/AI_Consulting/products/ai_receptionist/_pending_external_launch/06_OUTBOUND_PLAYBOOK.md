# AI Receptionist - Outbound Playbook (First 5 Targets)

**Owner**: Hammer + Piper
**Goal**: 1 close in 14 days. 5 discovery calls booked.
**Date**: 2026-04-21

---

## Target ICP (first 5)

Pick businesses where missed calls clearly cost money and where the owner is the decision-maker (avoid corporate buyers for MVP).

### Hard filters
- California-based (Hammer is local, easier for discovery calls)
- Single-location or small multi-location (under 5)
- Service-based (calls = bookings, not e-commerce)
- Owner-operated or small team (under 20 employees)
- Website shows a phone number on the homepage
- Yelp or Google Business profile has 20+ reviews (signals real volume)

### Verticals in priority order
1. Dental practices (high missed-call cost, $200+ per new-patient booking)
2. HVAC contractors (emergency calls, immediate revenue)
3. Law firms - personal injury, family (missed intake = lost client)
4. Med spas and beauty clinics (similar to video's Ivy Beauty Clinic example)
5. Real estate teams (time-sensitive leads)

## Prospect list generation

Use existing `prospect_scraper.py`:

```bash
python3 01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py \
  --vertical dentist --location "Sacramento, CA" --limit 20

python3 01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py \
  --vertical hvac --location "San Jose, CA" --limit 20

python3 01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py \
  --vertical legal --location "Oakland, CA" --limit 20
```

From the 60 scraped leads, Piper and Cipher hand-pick the best 5 based on:
- Review count (trust signal)
- Website has a basic booking mechanism (proves they want this problem solved)
- Phone number rings a real human during business hours (test call)
- No existing AI receptionist detected on test call

## Cold outbound - email sequence

### Email 1 (Day 0, Tuesday morning, from Piper)

**Subject**: Your Tuesday morning missed calls

**Body**:
> Hi [first name],
>
> I called [business name] Saturday night at 7:42 PM and got voicemail. I left one, but I'm guessing I'm not the only one who hung up.
>
> I help businesses like yours answer every call, 24/7, with a custom AI receptionist. It books, cancels, and reschedules appointments on your Google Calendar, in your business's voice. One-time build, monthly hosting, guaranteed 20% booking rate lift or we refund.
>
> Worth a 15-minute call? Here's my calendar: [link]
>
> Or hit reply with "demo" and I'll send you a 90-second audio of what it sounds like.
>
> Piper, Everlight Ventures
> piper@everlightventures.io

### Email 2 (Day 3, Friday morning, from Piper)

**Subject**: Re: Your Tuesday morning missed calls

**Body**:
> Hi [first name],
>
> Quick bump in case my first note got buried.
>
> Short version: we build AI phone receptionists for small service businesses in California. $4,500 build, $199/mo. Books on your Google Calendar, sends alerts to Slack or email, gets a local phone number that forwards back to you if you ever cancel.
>
> If it's a terrible fit, just hit reply and tell me why. I'll stop.
>
> If it's maybe worth a look: [calendar link].
>
> Piper

### Email 3 (Day 7, Tuesday afternoon, from Hammer)

**Subject**: [first name] - offering you a free test call

**Body**:
> Hey [first name], Hammer from Everlight.
>
> Piper wrote earlier. I run the close side. I'll cut the sales talk.
>
> If I can text you a number in 2 hours, and you can call it and have a full conversation with an AI Julie that could be your front desk tomorrow, would that be enough proof for a 15-minute call?
>
> Yes = reply "yes." I send you a demo line.
> No = reply "no" and I'm out of your inbox.
>
> Fair?
>
> Hammer
> hammer@everlightventures.io

### Email 4 (Day 10, Friday morning, from Hammer)

Only if no reply to all 3 above.

**Subject**: Closing the loop

**Body**:
> [first name], last one from me. Keeping this short.
>
> If you ever want to hear what a $4,500 AI receptionist sounds like for your business, here's a 90-second recording: [link]
>
> Otherwise I'll get out of your inbox. Cheers.
>
> Hammer

## Cold call script (if Piper prefers phone)

Use this if the prospect's business is one that clearly values live calls (HVAC, legal emergency).

```
[Business picks up]
PIPER: "Hi, is [owner first name] around? I know it's short notice."
RECEP: "He's with a client. Can I take a message?"
PIPER: "Sure. Tell him Piper from Everlight called. We build AI receptionists for HVAC shops so you never miss an after-hours call. I'm not selling anything today, I just want to know if he's ever lost a same-day emergency job to voicemail. If the answer's no, I'll stop. If it's yes, I'll send him a 90-second audio demo. Does he email, or is text better?"
RECEP: "Email. [email]."
PIPER: "Great. I'll fire one over in 10 minutes. Tell him I said hi."
[hang up politely]
[send personalized Email 1 within 10 minutes, referencing the call]
```

## Discovery call flow (30 min)

When one prospect books, Hammer runs the call.

1. **Opening (3 min)**: Thank you, pull up their website on screen, ask the warmup: "Before I say anything, tell me what you're losing most sleep over in the business right now."
2. **Problem deep-dive (10 min)**: Ask about call volume, peak hours, who answers now, what a missed call costs them. Write it down. Parrot it back.
3. **Demo (5 min)**: Play a 2-minute demo recording of a similar-vertical AI receptionist.
4. **Pricing + offer (5 min)**: $4,500 + $199/mo. 60-day guarantee. Go live in 14 days.
5. **Objection handling (5 min)**:
   - "I need to think about it" -> "What specifically are you unsure about?" (dig)
   - "Too expensive" -> "What's a missed call worth to you? If you gain 4 bookings a month at $300 average, this pays for itself in Month 2."
   - "What if my customers hate it?" -> "We run a soft launch. Half your calls route to the AI for the first week. You hear the recordings. We tune. If you're not sold, we stop and you pay nothing beyond the deposit." (Note: actual refund terms per contract.)
6. **Close (2 min)**: Send Stripe checkout link for the $2,250 deposit. If they don't pay on the call, schedule a follow-up in 3 days.

## Follow-up on signed deposit

Once deposit hits:
1. Piper sends intake form (services list, hours, FAQ doc, Google Calendar access)
2. Day 3: Forge delivers first draft of Vapi prompt + n8n flow
3. Day 7: Client reviews + approves demo
4. Day 10: Soft launch
5. Day 14: Full cutover + second payment ($2,250) auto-charges

## Success metrics (per deal)

- Deposit to signed contract: under 48 hours
- Intake form completion: under 5 days
- Time to soft launch: 7 business days
- Time to full cutover: 14 business days
- Client NPS at day 30: target 9+

## When to escalate

- Discovery call fails 3 times in a row: Piper + Hammer + Lucrex debrief what's breaking
- Deposit signed but intake stalls past 7 days: Piper calls personally, unblocks
- Client wants custom scope above product spec: route to Lucrex for go/no-go; default is no

## What NOT to do

- Do not offer discounts on the build fee (protects pricing anchor)
- Do not promise features not in the spec (guarantees surprise future work)
- Do not skip the soft launch (every bad first call kills renewals)
- Do not onboard a client who is not decision-maker (wastes 2 weeks of your time)
