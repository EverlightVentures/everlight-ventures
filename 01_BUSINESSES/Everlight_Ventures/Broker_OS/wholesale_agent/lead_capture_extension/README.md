# Everlight Lead Capture (Chrome Extension)

One-click capture of distressed / wholesale property listings into the pipeline.

## Load it (30 sec)
1. Chrome -> `chrome://extensions`
2. Toggle **Developer mode** (top-right) ON
3. Click **Load unpacked** -> select this folder (`lead_capture_extension/`)
4. Pin the extension. Open any listing on **Zillow / Redfin / Realtor / Trulia / Homes.com** and click the icon.

## What it does
- Scrapes the listing (address, price, beds/baths, sqft, state) from JSON-LD + meta + page text.
- **Distress score** (0-100) from keyword signals (as-is, motivated, probate, vacant, cash only, etc.).
- **TN flag**: green for Tennessee (active pipeline state), orange + "capture-only" for any other state, honoring the TN-only outreach law. Capture is allowed everywhere; only *outreach* is TN-only.
- Three actions:
  - **Copy** -> lead JSON to clipboard
  - **Save JSON** -> downloads `lead_*.json` (drop into the pipeline ingest)
  - **Send to pipeline** -> POSTs to the `notify-lead` Supabase edge function (emails the capture to hello@everlightventures.io with full metadata)

## Notes / next steps
- The "Send" sink reuses the existing `notify-lead` edge function (email). To persist captures into a Supabase table instead of (or in addition to) email, extend `notify-lead` to insert into `leads`/`web_leads` with `source='wholesale_capture'` -- then these flow straight into the broker pipeline.
- Selectors are heuristic (JSON-LD first, regex fallback). If a site changes layout and a field comes back blank, the regex in `popup.js extractListing()` is the place to tune.
- No build step, no dependencies, no tracking. Vanilla MV3. All values rendered via `textContent` (XSS-safe against hostile listing pages).
