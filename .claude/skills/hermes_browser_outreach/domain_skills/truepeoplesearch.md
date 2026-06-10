# domain skill: truepeoplesearch.com

**Purpose:** extract a property owner's EMAIL + phone from a name + city, free, for the
wholesale email pipeline (digital-only). Feeds tn_deal_tracker `email_needed -> email_found`.

## Reality (verified 2026-05-24)
- Plain HTTP GET (httpx, any IP incl. residential phone IP) returns **HTTP 403 + a Cloudflare
  JS challenge page** (~518 KB). The site is NOT scrapable without executing JavaScript.
- => REQUIRES a real browser executor: browser-use cloud (free tier) or headless Chromium.
  Do NOT waste run budget on plain-HTTP attempts; they always 403.

## Search URL pattern
`https://www.truepeoplesearch.com/results?name={FIRST}%20{LAST}&citystatezip={CITY}%2C%20{STATE}`

## Browser-use task (natural language, what Hermes runs)
1. Open the results URL. Wait for the Cloudflare challenge to clear (browser-use handles it).
2. On the results list, click the FIRST person card whose city matches the target city.
3. On the detail page, extract: full name, age, current address, phone numbers (with type),
   and email addresses (the "Email Addresses" section is usually mid-page, sometimes collapsed --
   click "View All" if present).
4. Return JSON: `{name, address, city, state, emails:[...], phones:[...], match_confidence}`.

## Match guard (anti-wrong-person)
Only accept a contact if the detail page's LAST NAME matches the owner's last name AND the
city/state matches. Common names (e.g. "John Smith") with no address corroboration => reject
(`match_confidence: low`), never email. Wrong-person email = a complaint = the thing we avoid.

## Gating (mandatory, post-extract)
Every extracted email/phone passes `eradication_gate.find_hit()` + opted_out check + TN
`state_gate` BEFORE it touches the tracker. A hit = drop the row, log it.

## Cost
$0 on browser-use cloud free tier (first 30 days). Then e5-mother headless Chromium ($0,
owned). Never a paid skip-trace API (feedback_frugal_build_dont_buy).
