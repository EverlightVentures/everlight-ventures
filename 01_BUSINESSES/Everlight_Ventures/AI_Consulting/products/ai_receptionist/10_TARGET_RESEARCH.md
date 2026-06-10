# First 5 Targets - Research + Curation Template

**Owners**: Cipher (research) + Piper (qualify)
**Status**: Blocked on data source. See "Unblock path" below.
**Date**: 2026-04-21

---

## Current blocker

The existing `prospect_scraper.py` needs Google Maps Places API billing enabled on the GCP project. Live test returns `REQUEST_DENIED: You must enable Billing`.

### Unblock path A (recommended, 3 minutes)

1. Open https://console.cloud.google.com/
2. Top dropdown -> pick the project attached to the `GOOGLE_MAPS_API_KEY`
3. Left nav -> **Billing** -> **Link a billing account**. Free-tier monthly credit ($200 Maps, $300 general) covers hundreds of scrapes per month.
4. Left nav -> **APIs & Services** -> **Library** -> search "Places API" -> **Enable**
5. Re-run: `python3 01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py --vertical dentist --location "Sacramento, CA" --limit 10`

### Unblock path B (manual, 30 minutes)

For the first 5 targets, skip automation. Cipher uses Google Maps web UI + Yelp public pages to hand-pick. No API key required.

For each candidate found, fill the template below.

---

## Target profile template (fill one per candidate)

Copy this block into `first_5_targets.md` once curated.

```markdown
### Target <N>: <Business Name>

**Vertical**: <dentist / HVAC / legal / med-spa / real-estate>
**Location**: <City, CA>
**Owner / Decision-maker**: <Full Name, or "unknown - call to find out">
**Website**: <URL>
**Phone**: <xxx-xxx-xxxx>
**Email**: <admin@domain, or "scrape from website contact page">

**Signals of fit** (check at least 3):
- [ ] 20+ Google reviews (proves real call volume)
- [ ] Single location or < 5 locations (owner decides fast)
- [ ] Visible "Book Appointment" or "Call Us" button on site (they want this solved)
- [ ] No chatbot / AI phone on the website yet (no incumbent)
- [ ] Phone number on homepage (calls matter to them)
- [ ] Website looks active / recent (email addresses will be live)

**Signals of NOT a fit**:
- Franchise or corporate (decision is not local)
- HIPAA-strict (add $2K HIPAA tier, longer sales cycle)
- Under 10 reviews (not enough volume to justify the fee)

**Piper's warm-up angle** (personalize to this business):
- <one sentence mentioning something specific from their Google reviews, website, or a visible pain>

**Test-call result** (place one call outside business hours):
- Picked up: Y/N
- Voicemail: Y/N
- After-hours greeting quality: good / basic / missing

**Decision**: PITCH / RESEARCH MORE / SKIP
```

## Verticals + cities for the first 5

Target **one from each** combination below. This gives Hammer vertical diversity (different talking points per call) and geographic diversity (different area codes for Twilio).

| # | Vertical | Primary city | Backup city |
|---|---|---|---|
| 1 | Dentist / dental practice | Sacramento, CA | San Jose, CA |
| 2 | HVAC contractor | Fresno, CA | Modesto, CA |
| 3 | Law firm (personal injury or family) | Sacramento, CA | Oakland, CA |
| 4 | Med spa / beauty clinic | San Jose, CA | Berkeley, CA |
| 5 | Real estate team | Oakland, CA | Walnut Creek, CA |

## Quick-curation workflow (for path B, 30 min total)

Per target (6 min each):
1. Open Google Maps. Search "<vertical> in <city>".
2. Filter: Rating >= 4.2, >= 30 reviews, open now.
3. Pick one where the phone number is on the listing.
4. Click through to the website. Note whether the site has a booking button, current-looking design, and a visible owner name ("Meet Dr. X" or "Owner John Doe").
5. Open the contact page. Copy the email (or grab it via the site footer).
6. Place a 1-minute test call outside business hours (or during lunch). Note the voicemail quality.
7. Fill the template above.

## If Cipher wants free API-less help

Use:
- **Yelp Fusion API** (free tier): https://www.yelp.com/fusion (different auth, no billing setup)
- **OpenStreetMap Nominatim**: addresses but no ratings/reviews
- **LinkedIn search** (logged in): "owner <vertical>" filtered to CA
- **Yellow Pages** (free): https://yellowpages.com, less-fresh data but OK signal

Recommended: Yelp Fusion API. It's cleaner than Maps for small-business discovery and does not require billing setup. We'd need to swap one function in `prospect_scraper.py` to use it. About 45 min of Forge time.

## Sample target (to show the format, NOT a real lead to contact)

### Target EXAMPLE: Placeholder Dental Sacramento

**Vertical**: Dentist
**Location**: Sacramento, CA
**Owner**: Dr. Example (unverified)
**Website**: example-dental.com
**Phone**: 916-555-0100
**Email**: info@example-dental.com (from contact page)

**Signals of fit**:
- [x] 47 Google reviews
- [x] Single location
- [x] "Schedule Online" button on homepage
- [x] No AI phone detected
- [x] Phone on header
- [x] Site updated within last 12 months

**Piper's warm-up angle**:
"I saw your reviews mention a receptionist named Maria that everyone loves. This is not about replacing Maria. This is about what happens to callers when Maria is not at the desk."

**Test-call result**:
- Picked up: N (after 7 PM)
- Voicemail: Y
- Greeting: basic, no callback promise

**Decision**: PITCH

*(This example is fictional. Use as formatting reference only. Do not contact.)*

## Success criterion for this step

Once Cipher or Piper delivers the first 5 real targets populated with this template, Hammer sends Email 1 on the next Tuesday morning per the playbook.

Target timeline: 5 real targets delivered within 48 hours of unblocking the data source (GCP billing OR manual curation).
