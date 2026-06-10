# Landing Page Spec: /ai-receptionist

**Target route**: `everlightventures.io/ai-receptionist`
**Stack**: React + Vite + Shadcn/UI + Tailwind (matches existing site conventions)
**Owner**: Piper (copy) + writer (polish)
**Status**: Content-ready. Needs a React engineer to create the page component + add to router.

---

## Meta

- Title: `Everlight AI Receptionist | Never Miss Another Call`
- Description: `A custom AI phone receptionist for small businesses. $4,500 build, $199/mo. Books and cancels appointments 24/7. 60-day booking-rate guarantee.`
- OpenGraph image: Everlight gold logo + headline "Your Front Desk Never Sleeps"

## Section 1 - Hero

**Headline**: Your front desk never sleeps.
**Subheadline**: A custom AI receptionist that answers every call, in your business voice, on your calendar. $4,500 build, $199 per month.
**Primary CTA**: Book a 30-Minute Discovery Call (links to Calendly or Tally form)
**Secondary CTA**: Listen to a Demo Call (plays audio)
**Visual**: short looping video of a phone ringing, being picked up by the AI, showing a booking confirmation on a calendar.

## Section 2 - Problem statement

**Heading**: Missed calls are lost revenue.
**Body**: 62% of SMB inbound calls that hit voicemail never become a booking. You lose five figures a year to a phone you cannot answer at 7 PM on a Wednesday.
**Stat bar** (3 tiles):
- **62%** of voicemails never book
- **168 hours** your phone rings each week
- **$5,400/mo** average receptionist salary in California

## Section 3 - What you get

Use 2-column layout. Left: bullet list of build deliverables. Right: bullet list of monthly hosting.

**One-time build ($4,500)**
- Custom voice matched to your brand
- Your services, your pricing, your hours
- Google Calendar integration (book, cancel, reschedule)
- FAQ knowledge base loaded from your docs
- Slack or email alerts
- Live call log dashboard
- Two weeks of tuning after go-live

**Monthly hosting ($199)**
- Up to 200 calls included
- Dedicated local phone number
- 24/7 uptime monitoring
- Monthly usage report
- Priority support in under 4 hours

## Section 4 - Demo transcript

Styled as a phone-call bubble UI (receptionist on left, caller on right).

```
Julie (AI): "Hi, this is Julie from Ivy Beauty Clinic. How can I help?"
Caller: "I want to reschedule my appointment."
Julie: "Sure, can I get your first name?"
Caller: "Audrey."
Julie: "Thanks Audrey. I found your appointment March 7th at noon. Move it?"
Caller: "Yes, tomorrow at 1 PM."
Julie: "Tomorrow at 1 PM works. What service?"
Caller: "Free consultation."
Julie: "Booked. Your original is cancelled, new slot tomorrow at 1 PM. Enjoy your day."
```

## Section 5 - How it works

Stepper component, 4 steps:
1. **Discovery call** - 30 min. We learn your business, services, call volume.
2. **Build phase** - 7 days. We prompt your AI, integrate your calendar, load your FAQs.
3. **Soft launch** - 1 week. AI handles half your inbound while we tune.
4. **Full cutover** - AI handles all calls. 30-day review with you.

## Section 6 - Who this is for

3-column card grid:
- **Service businesses** - HVAC, plumbing, electricians, cleaners
- **Medical and dental** - single-provider and small practices
- **Professional services** - lawyers, accountants, real estate

Second row (smaller):
- Salons, spas, wellness
- Home improvement
- Any SMB with 20+ inbound calls per month

## Section 7 - Guarantee

**Heading**: 60-day booking rate guarantee.
**Body**: If your booking rate doesn't improve by 20% in the first 60 days, we refund the monthly hosting back to day one. We keep the build fee because we built it for you.
**Trust badges**: "Everlight Ventures" logo, "Powered by Vapi + Google" stamp, refund-check icon.

## Section 8 - Pricing (repeated, with CTA)

Two cards side-by-side:
- **Standard** - $4,500 + $199/mo. "Start here"
- **White-Label Plus** - $7,500 + $399/mo. "Hidden Everlight branding. Custom admin portal for your team." _Tag: Coming soon, join waitlist._

CTA on each: "Book Discovery Call" and "Join Waitlist."

## Section 9 - FAQ

Accordion component:
1. How long until I'm live? (7 to 21 days)
2. Can it integrate with my CRM? (Yes - Google Sheets, HubSpot, Zoho, custom API)
3. What if someone wants a human? (Warm transfer or voicemail-to-Slack)
4. Is it HIPAA-compliant? (Standard tier: no. HIPAA tier available, add $2,000)
5. Can I change the voice? (Yes - 20+ voices, you pick at onboarding)
6. What happens if I cancel? (Your phone number forwards back to you within 24 hours)

## Section 10 - Final CTA

**Heading**: Your phone is about to ring. Make sure someone answers.
**Primary CTA**: Book a Discovery Call
**Secondary CTA (small)**: Email hammer@everlightventures.io

## Footer

Standard Everlight footer (shared component).

---

## TSX scaffold (for the engineer)

```tsx
// src/pages/AiReceptionistPage.tsx
import { Hero } from "@/components/sections/Hero";
import { ProblemStats } from "@/components/sections/ProblemStats";
import { Deliverables } from "@/components/sections/Deliverables";
import { DemoTranscript } from "@/components/sections/DemoTranscript";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { WhoItsFor } from "@/components/sections/WhoItsFor";
import { Guarantee } from "@/components/sections/Guarantee";
import { PricingCards } from "@/components/sections/PricingCards";
import { FaqAccordion } from "@/components/sections/FaqAccordion";
import { FinalCta } from "@/components/sections/FinalCta";

export function AiReceptionistPage() {
  return (
    <main className="min-h-screen bg-ev-ink text-ev-cream">
      <Hero ... />
      <ProblemStats ... />
      <Deliverables ... />
      <DemoTranscript ... />
      <HowItWorks ... />
      <WhoItsFor ... />
      <Guarantee ... />
      <PricingCards ... />
      <FaqAccordion ... />
      <FinalCta ... />
    </main>
  );
}
```

Register in router: add `<Route path="/ai-receptionist" element={<AiReceptionistPage />} />` in App.tsx.

Add to main nav: under "Services" dropdown, new item "AI Receptionist."

## Analytics

Add PostHog or GA4 events:
- `ai_receptionist_page_view`
- `ai_receptionist_discovery_click` (primary CTA)
- `ai_receptionist_demo_audio_play`
- `ai_receptionist_waitlist_click` (white-label)
- `ai_receptionist_faq_open` with question-id

## Open for engineering

- Calendly vs Tally for the booking form (Tally matches existing funnel pages)
- Audio hosting for demo call (Oracle nginx or Cloudflare R2)
- Phone-number masking for the demo transcript visuals
