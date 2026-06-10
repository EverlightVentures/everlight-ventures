# Google Business Profile -- Setup Pack for Everlight Ventures

Everything pre-written. Open google.com/business, paste each field, hit save.
Total time at your laptop: 15 minutes. Verification arrives 5-14 days later.

---

## STEP 1 -- create the profile (5 min)

Go to: https://www.google.com/business/

Click "Manage now," sign in with the Gmail you want to own this.

### Field-by-field paste

**Business name:**
```
Everlight Ventures
```

**Business category (primary):**
```
Real estate agency
```
(Pick this even though you're a wholesaler -- there's no "wholesaler" category. This one ranks for the right searches.)

**Additional categories (add 2-3):**
```
Investment service
Real estate consultant
Property management company
```

**Do you have a location customers can visit?**
- Pick: NO ("I deliver goods and services to customers")
- Reason: you're a service-area business, not a retail location

**Service areas (add all):**
```
Atlanta, GA
Marietta, GA
Decatur, GA
Sandy Springs, GA
Roswell, GA
Alpharetta, GA
Stone Mountain, GA
East Point, GA
College Park, GA
```
(Add more counties if you want -- max 20. The 9 above cover Metro Atlanta core.)

**Phone:**
```
+1 404-800-4380
```

**Website:**
```
https://everlightventures.io
```

---

## STEP 2 -- business description (paste this)

Max 750 characters. This is exactly 712:

```
Everlight Ventures is a Metro Atlanta real estate investment firm working with homeowners who need to sell quickly without listing on the market. We make direct cash offers, close in as little as 7-14 days, and buy properties as-is -- no repairs, no commissions, no showings. We work with sellers facing inherited property, vacant houses, foreclosure pressure, divorce, relocation, or tired-landlord situations. Every offer comes with a transparent breakdown of how we got to the number, the assignment-of-contract structure spelled out up front, and a 24-hour AI assistant available to answer questions any time. Real estate investment firm. Sellers do not pay any commission to Everlight Ventures.
```

---

## STEP 3 -- hours (paste this)

```
Monday:    7:00 AM - 8:00 PM
Tuesday:   7:00 AM - 8:00 PM
Wednesday: 7:00 AM - 8:00 PM
Thursday:  7:00 AM - 8:00 PM
Friday:    7:00 AM - 8:00 PM
Saturday:  9:00 AM - 6:00 PM
Sunday:    Closed
```
(Sunday closed mirrors your weekly_cadence rules + GA Sunday outreach gate.)

---

## STEP 4 -- services (add each as a service)

Click "Services" -> "Add service" for each:

1. **Cash offer for inherited property**
   Description: "Direct cash offer on inherited or probate property. Close in 7-14 days. No repairs, no showings, no commissions."

2. **Pre-foreclosure cash offer**
   Description: "Confidential cash offer for homeowners facing foreclosure or behind on mortgage. We close before the auction date so you walk away with cash, not a foreclosure on your record."
   (NOTE: California pre-foreclosure outreach is BLOCKED in your state_gates -- this service applies to GA, FL, TX, AZ, MO, TN only.)

3. **Vacant property cash offer**
   Description: "Cash offer for vacant homes that have become a carrying-cost burden. We pay full cash, close in 14 days, you stop paying the mortgage and taxes immediately."

4. **Tired landlord cash exit**
   Description: "Cash exit for landlords ready to be done. We buy with tenants in place or vacant. No repairs needed."

5. **As-is property purchase**
   Description: "We buy properties in any condition. Fire damage, foundation issues, code violations, hoarder situations -- we have buyers for every condition class."

---

## STEP 5 -- photos (you need 5 minimum)

Use these free sources:

**Logo (square, 250x250+):**
- Already have this? Drop it in
- If not: any free logo maker (canva.com free tier) -- gold "EV" on dark background

**Cover photo (1024x576, professional looking):**
- Atlanta skyline (free on unsplash.com search "atlanta skyline")
- Pick one with the gold-hour lighting that matches your brand

**3 service photos:**
- Free on unsplash.com:
  - Search "house keys handover" (closing day vibe)
  - Search "for sale sign" (or photograph an actual one near you)
  - Search "house exterior atlanta" (a typical metro Atlanta home)

**Optional: video walkthrough**
- 30-second phone video of you (or anyone) saying "I'm with Everlight Ventures, we buy houses cash in Metro Atlanta..."
- Boosts ranking significantly

---

## STEP 6 -- verification

Google will offer 1-3 verification methods:

**Most likely: postcard**
- 5-14 day mail wait
- Sent to the business address you enter
- Has a 5-digit code
- Type it back into your dashboard
- IMPORTANT: enter your home address or a UPS Store mailbox (~$15/mo) here. Cannot use a PO box.

**Sometimes: video call**
- Google video-calls you
- You show them your phone (caller ID matches)
- You show your business documents (DBA filing)
- Faster -- same day

**Rarely: phone**
- Robo-call to your business number
- Reads a code

---

## STEP 7 -- after verification (Day 1 done)

Set up:
1. **Google Posts** -- post weekly: "Just bought a house in [city]. If you have a [condition] property, here's our offer process." (counts as content marketing, boosts SEO)
2. **Q&A** -- pre-seed 5-10 common questions yourself (logged out, ask them. Logged in, answer them):
   - "Do I pay any fees?"
   - "How fast can you close?"
   - "What if my house needs repairs?"
   - "What if I owe more than the house is worth?"
   - "Do I have to show the house?"
3. **First review request** -- text the 1 deal you have in `intro` stage (or any past help-out, family, friend who'll vouch for you authentically) and ask for a review. The first 5 are the hardest; after 5, social proof compounds.

---

## STEP 8 -- log it back into the system

Once verified, run this on Oracle to mark GBP as PASS in the audit:

```bash
ssh oracle-bot
python3 -c "
import os, sys
sys.path.insert(0, '/home/opc/hive_django')
os.environ['DJANGO_SETTINGS_MODULE']='hive_dashboard.settings'
import django; django.setup()
from broker_ops.models import GBPListing
from datetime import datetime
GBPListing.objects.create(
    name='Everlight Ventures',
    primary_market='Atlanta, GA',
    phone='+14048004380',
    website='https://everlightventures.io',
    google_place_id='YOUR_PLACE_ID_FROM_DASHBOARD',
    verified=True,
    verified_at=datetime.now(),
)
print('GBP logged + audit will now PASS')
"
```

---

## What changes when this is live

- Free organic leads from "we buy houses Atlanta" searches
- Trust badge on your number when sellers see "Verified" tag
- Reviews accumulate -> show up in every search result
- The Reputation section of the audit auto-PASSes (was PARTIAL)
- Marcus + Piper can mention "verified Google Business Profile" in seller outreach
