# EVERLIGHT VENTURES -- /sell PAGE
# Seller Acquisitions Landing Page for everlightventures.io
# Push to Lovable via GitHub -- add as new route /sell

## ROUTE: /sell

## PURPOSE
Landing page for property sellers. Rex (our wholesale acquisition bot) links
to this page in every outreach email. When sellers Google "Everlight Ventures"
and click through, they see a professional acquisitions page and can submit
their property for a cash offer.

## DESIGN
Same global design system as the rest of the site:
- Background: #0A0A0A (Void Black)
- Cards: #1A1A1A with border #2A2A2A
- Gold Accent: #D4AF37 (Everlight Gold)
- Heading: Inter 700
- Body: Inter 400
- Shared top nav

## SUPABASE INTEGRATION
Form submissions go to `seller_leads` table (already created):
```sql
INSERT INTO seller_leads (name, email, property_address, phone, source)
VALUES ($name, $email, $address, $phone, 'landing_page');
```
Use the existing Supabase client from the project.

======================================================================

## HERO SECTION

**Badge:** PRIVATE ACQUISITIONS

**Headline:** Get a **Cash Offer** for Your Property

**Subhead:** We buy properties as-is for cash. No agents, no fees,
no repairs. Close in as little as 7 days.

**CTA Button:** [Get My Cash Offer] -- scrolls to form

## STATS BAR

Three animated counters in a row:
- **7-Day** Average Close
- **100%** Cash Offers
- **6** Active Markets

## HOW IT WORKS

Three cards with step numbers:

**01 -- Submit Your Property**
Fill out the form with your property details. Takes 30 seconds. No obligation.

**02 -- Receive a Cash Offer**
Our acquisitions team reviews your property and delivers a written cash
offer within 24 hours.

**03 -- Close on Your Timeline**
Pick your closing date. We handle title, paperwork, and all costs.
You show up and get paid.

## CONTACT FORM

Card with gold border glow on the form section.

**Heading:** Get Your **Cash Offer**
**Subhead:** No fees. No commissions. No obligation.

Fields:
- Full Name (required)
- Email (required)
- Property Address (required)
- Phone (optional)

**Submit Button:** [GET MY CASH OFFER] -- gold glow button

**On submit:**
1. Insert into Supabase `seller_leads` table
2. Show success state with checkmark animation:
   "Request Received -- Our acquisitions team will review your property
   and send a written cash offer within 24 hours."

## WHY SELLERS CHOOSE US

Four benefit cards:

- **Licensed & Insured** -- Fully licensed operation backed by Everlight Logistics LLC.
- **Professional Acquisitions** -- Institutional-grade due diligence on every property.
- **Nationwide Portfolio** -- Active acquisitions across 6 major metro markets.
- **7-Day Close** -- Cash on hand. No bank delays, no financing contingencies.

## CURRENTLY SERVING

Market tags (pill badges):
Atlanta, GA | Dallas, TX | Cleveland, OH | St. Louis, MO | Jacksonville, FL

## FOOTER

Standard site footer.

======================================================================

## NOTES FOR LOVABLE BUILD

- Add /sell to the router in App.tsx
- Add "Sell Your Property" to the nav menu (or keep it unlisted --
  Rex links to it directly in emails)
- The form MUST save to Supabase seller_leads table on submit
- Gold accent matches the rest of the site (#D4AF37)
- Page should be mobile-first -- most sellers will click from a
  text/email on their phone
- Include smooth scroll from hero CTA to form
- Animated stat counters on scroll into view
