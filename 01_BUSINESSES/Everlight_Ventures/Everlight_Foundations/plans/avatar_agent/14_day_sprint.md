# Everlight Content Engine + Funnel -- 14-Day Install Sprint
Hive Sessions: 84a032cf + 1a74a4f2 | Updated: 2026-03-05

## Goal
Stand up a working content pipeline + marketing funnel for Onyx POS and Hive Mind SaaS.
All tools run on YOUR stack: ffmpeg, Django, Python smtplib, direct API posting.

---

## Week 1 -- Content Pipeline (Days 1-7)

### Day 1-2: Avatar Assets + Voice Setup
- [ ] Generate 3-5 avatar portrait images (Midjourney/DALL-E/free generator)
  - Save to: `01_BUSINESSES/Everlight_Ventures/03_Content/Avatar_Assets/base_portraits/`
  - Need at minimum: `default.jpg`, `eli_founder.jpg`, `sage_builder.jpg`
- [ ] Sign up ElevenLabs free tier, create 2 voices, save IDs to `.env`
- [ ] Test dry run: `python avatar_orchestrator.py --dry-run --product onyx --count 1`

### Day 3-4: First Real Content Batch
- [ ] Run Onyx POS batch: `python avatar_orchestrator.py --product onyx --persona founder --count 3`
- [ ] Run Hive Mind batch: `python avatar_orchestrator.py --product hivemind --persona builder --count 3`
- [ ] Review output in `02_CONTENT_FACTORY/01_Queue/avatar_output/`
- [ ] Post 1 video manually to TikTok/Reels

### Day 5-6: Social Distribution Setup
- [ ] Apply for X/Twitter developer API access (free v2)
- [ ] Test social_poster.py: `python social_poster.py --dry-run`
- [ ] Configure Slack #04-content-factory for manual upload queue (TikTok/IG)

### Day 7: Review + Calibrate
- [ ] Watch posted videos -- note hook timing, pacing, caption clarity
- [ ] Adjust persona tone, TTS voice, or script prompts
- [ ] Document what worked in `plans/avatar_agent/lessons.md`

---

## Week 2 -- Funnel + Automation (Days 8-14)

### Day 8-9: Django Funnel App
- [ ] Register domain (onyxpos.io or similar, ~$12/yr)
- [ ] Run Django migrations: `python manage.py migrate`
- [ ] Verify landing pages: `python manage.py runserver 0.0.0.0:8504`
  - `/onyx/` -- Onyx POS landing page
  - `/hivemind/` -- Hive Mind waitlist page
- [ ] Set up Stripe account for payment processing

### Day 10-11: Email Nurture
- [ ] Pick SMTP provider (Resend/Brevo/Proton), get credentials
- [ ] Configure SMTP env vars in `.env`
- [ ] Test email sequence: `python funnel_nurture.py --dry-run`
- [ ] Add cron job for hourly nurture checks

### Day 12-13: Automation + Cron
- [ ] Add content gen cron: daily at 6 AM PT
- [ ] Add social posting cron: 8 AM + 12 PM PT
- [ ] Add nurture cron: hourly check
- [ ] Verify Slack notifications flowing to correct channels

### Day 14: Metrics Review + Kill/Scale
- [ ] Check funnel dashboard metrics
- [ ] Apply kill_scale_rubric.yaml scoring:
  - Opt-in rate >= 10%
  - Zero tripwire sales after 14 days = kill signal
- [ ] Apply phase_gate_checklist.yaml for launch readiness

---

## Tool Stack (Actual -- No External SaaS Dependencies)

| Function | Tool | Cost |
|---|---|---|
| Script Gen | Claude API (claude-opus-4-6) | Per-token |
| TTS | ElevenLabs Turbo v2 | Free tier |
| Video Gen | ffmpeg Ken Burns slideshow | Free |
| Video Gen (Tier 2) | D-ID API lip-sync | Free tier (5 min) |
| Landing Pages | Django funnel app | Free (self-hosted) |
| Email Nurture | Python smtplib + Resend/Brevo | Free tier |
| Social Posting | Python + X/LinkedIn APIs | Free |
| Analytics | Django + Streamlit dashboard | Free |
| Checkout | Stripe | Per-transaction |

---

## Files

| File | Purpose |
|---|---|
| `03_AUTOMATION_CORE/01_Scripts/avatar_orchestrator.py` | Content pipeline (ffmpeg + D-ID) |
| `03_AUTOMATION_CORE/01_Scripts/social_poster.py` | Direct API social posting |
| `03_AUTOMATION_CORE/01_Scripts/funnel_nurture.py` | Email drip runner |
| `09_DASHBOARD/hive_dashboard/funnel/` | Django landing pages + lead capture |
| `03_AUTOMATION_CORE/02_Config/funnel_emails/` | Email sequence configs + templates |
| `plans/avatar_agent/personas.json` | 5 personas (3 crypto + founder + builder) |
