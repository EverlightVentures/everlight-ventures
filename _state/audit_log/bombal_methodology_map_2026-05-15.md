# Bombal OSINT Methodology Map -- 2026-05-15

**Author**: Cipher Wolfe (Perplexity Intel) + everlight_researcher
**Use case**: Real-estate wholesale seller outreach + Open Deal buyer vetting. NOT security. NOT surveillance. "Google-grade personalization" -- signals invisible, output relevant.
**Sources**: 6 transcripts in `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/` (cited inline) + 1 WebSearch pass for collabs not in transcripts.

---

## A. Bombal's Canonical OSINT Stack (recurring across guests MJ Banias, Mishaal Khan, John Hammond, who-am-i-10)

Cross-referenced from `top_7_osint_tools_revealed.txt`, `osint_tools_to_track_you_down.txt`, `how_to_find_anyone_online.txt`, `google_dorking_find_everything.txt`. Tools that appear in 2+ episodes are weighted highest.

| Tier | Tool | Use | Episodes |
|---|---|---|---|
| Core | **WhatsMyName.app** (OSINT Combine) | Username -> ~500 sites | top_7, find_anyone |
| Core | **Maigret** (CLI, fork of Sherlock) | Username -> 500 sites + bio extraction (location, followers) | find_anyone, osint_tools |
| Core | **Sherlock** | Username -> account presence | find_anyone |
| Core | **theHarvester** | Domain -> emails + subdomains via passive DNS | find_anyone |
| Core | **Google dorks** (`site:`, `filetype:`, `intitle:`, `inurl:`, `"exact"`, `-negate`) + **dorkGPT**, **DorkSearch.pro** | Surface "hidden" public docs | google_dorking, top_7 |
| Core | **Newspapers.com** + **Judy Records** | Old archives, court records, relatives, birth/marriage announcements | top_7 |
| Core | **OSINT Industries** ($20/mo) + **Epieos** | Email/phone -> accounts + breach timeline | top_7, osint_tools |
| Core | **Have I Been Pwned** + raw breach files (ripgrep on local CSV) | Email -> breach hits + linked PII | osint_tools |
| Core | **WHOXY** + **whois** | Domain -> historical registrants + reverse-owner | osint_tools |
| Core | **Archive.org Wayback** | Old versions of pages w/ leaked PII | osint_tools |
| Cap | **Maltego** + **Hunchly** (now merged) | Graph + evidence capture (pro tier) | top_7 |
| Cap | **Ubiquron** (Vortimo, free) / **Forensic OSINT** | Browser-side investigation capture, autoscroll PDF, selector extraction | top_7 |
| Cap | **Kagi** ($5/mo) | Ad-free search, small-web/forums/PDF filter, geo-scope | top_7 |
| Cap | **Wigle.net** | Address -> Wi-Fi SSIDs at location | osint_tools |
| Cap | **Sync.me / Truecaller** (Android emulator route) | Phone -> crowdsourced contact name | osint_tools |
| Cap | **Obsidian Canvas** mind-map | Pivot management, anti-rabbit-hole | osint_tools |

**Mindset doctrine** (Banias, top_7): "It's not the tools, it's the gum-chewing." Bombal's recurring frame is that OSINT is a research mindset; tools are accelerants. Mishaal's redundancy doctrine (osint_tools): never rely on one tool; same query across 3-5 sources is due diligence.

Recent collabs (WebSearch 2026): Bombal x Mishaal Khan at Black Hat on anti-OSINT/privacy; Bombal x NetworkChuck "This is IT!" weekly podcast. No new tool stack vs the 6 transcripts -- collabs reinforce existing canon.

---

## B. What We Already Have (cross-ref to `06_DEVELOPMENT/everlight_os/intel_center/osint_api/investigators/`)

| Bombal tool/pattern | Our module | Status |
|---|---|---|
| Google dorks | `google_dorks.py` | Have |
| theHarvester / domain recon | `domain_intel.py` + `whois_lookup.py` | Have |
| HIBP / breach lookup | `leak_check.py` | Have |
| Court records (Judy) | `public_records.py` | Have |
| Archive.org Wayback | `archive_org.py` | Have |
| WHOIS historical | `whois_lookup.py` (verify WHOXY-style history) | Partial |
| Skip-trace | `skip_trace.py` | Have |
| Social/username presence | `social_recon.py`, `social_bio_scraper.py` | Have |
| Corporate (OpenCorporates) | `opencorporates.py` | Have |
| Property records | `property_records.py` | Have |
| SEC | `sec_edgar.py` | Have |
| Philanthropy/civic | `philanthropy_civic.py` | Have |
| Consumer signals | `consumer_signals.py` | Have |
| Resource lookup | `resource_lookup.py` | Have |

18 modules covers ~70% of Bombal's canonical surface.

---

## C. Gaps We Can Ethically Port

Out-of-scope by Rich's directive (DPPA plates, FCRA backgrounds, hotel-portal exploit, voter-ID iteration, breach-data CSV, Wigle SSID at address) -- skip. The "Google version" rule keeps us on PUBLIC PROPERTY + PUBLIC NEWS + PUBLIC CORPORATE signals.

Net-new patterns worth porting:
1. **Newspapers + obituaries** (top_7) -- estate/heir hooks for distressed-property outreach.
2. **WhatsMyName/Maigret username enumeration** (find_anyone) -- light upgrade to existing `social_recon`, add ~500-site coverage.
3. **Reverse-WHOIS via WHOXY** (osint_tools) -- which other domains does this LLC own? Useful for buyer vetting.
4. **Wayback selector extraction** -- pull old contact info LLCs scrubbed.
5. **Kagi small-web/PDF search** as a Google-dorks backstop (forum mentions, local-paper PDFs).

---

## D. Recommended Top-5 Ports (ranked by wholesale ROI)

| # | New investigator | What it does | Wholesale use case | Effort | Creep-line |
|---|---|---|---|---|---|
| 1 | `obituary_estate.py` | Newspapers.com + Legacy.com + Tributes.com search by surname + town + decade | Estate/heir leads: 28 of our 114 parsed parcels are owner-deceased or estate-flagged (Howard Eddie Estate, Leggett Bennie etc). Hook: "saw the announcement for [parent], my condolences -- if the family is dealing with the property..." | **S** (2 days) | GREEN. Obits are published-on-purpose. Same data a funeral home or genealogist uses. |
| 2 | `username_enrichment.py` (WhatsMyName + Maigret wrapper) | Username -> bio/location/follower hooks across 500 sites | Buyer vetting (Inner Circle $99): does claimed identity match digital footprint? Cuts catfish/straw-buyer risk pre-Stripe-Identity. | **S** (1 day) | GREEN for buyers (they paid us to vet). YELLOW for sellers -- only run if seller already gave us their handle. |
| 3 | `reverse_whois.py` (WHOXY historical + reverse-owner) | Domain -> historical registrants; email/name -> all domains they registered | Buyer LLC due diligence: surfaces flip history, shell-co patterns, prior LLCs same operator. | **S** (1 day, API key paid tier ~$10) | GREEN. Public registrar data. |
| 4 | `local_news_archive.py` (Kagi small-web API + Newspapers.com scrape) | Address/owner -> local-paper mentions, code-violation citations, zoning hearings | Personalization: "saw the [town]-Press piece on your block's rezoning hearing -- curious if that's part of why you're thinking about selling." Google-grade relevance. | **M** (4 days; Kagi paid API + Newspapers cookie session) | GREEN if cited only in soft language ("noticed the rezoning in your area"). RED if we quote citations back to the owner verbatim. Guardrail: redact specifics, reference neighborhood-level only. |
| 5 | `wayback_contact_extract.py` | Wayback Machine -> historical contact info on owner LLC sites | Skip-trace fallback when current site scrubbed; surfaces old emails/phones for shell LLCs hiding behind privacy WHOIS. | **M** (3 days) | YELLOW for individuals (use only when their site listed contact publicly). GREEN for LLCs (they chose to publish). |

**Hard skip list** (do not build): plate-to-VIN (DPPA), voter-ID iteration (Mishaal demo, federal mess), breach-data CSV ripgrep (FCRA + GLBA + civil liability), Wigle SSID-at-address (creepy and useless for wholesale), Burp-Suite form brute (CFAA exposure).

**Creep-line rule** -- if the output of an investigator would make a seller feel watched rather than helped, the signal stays internal (used to score lead priority) but never appears in outbound copy. Personalization hook: "noticed the area is rezoning." Surveillance: "noticed your son just graduated UT-Knoxville." Same data source, opposite ethics.

---

## Sources (relevance)

- [top_7_osint_tools_revealed.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/top_7_osint_tools_revealed.txt) -- MJ Banias 2026 canonical stack
- [osint_tools_to_track_you_down.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/osint_tools_to_track_you_down.txt) -- Mishaal Khan 3-tier + redundancy doctrine
- [how_to_find_anyone_online.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/how_to_find_anyone_online.txt) -- WhoAmI10 username pivot workflow
- [google_dorking_find_everything.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/google_dorking_find_everything.txt) -- operator reference
- [is_hexstrike_the_best_ai_mcp_for_security.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/is_hexstrike_the_best_ai_mcp_for_security.txt) -- HexStrike (skipped: offensive sec, not our lane)
- [fabric_opensource_ai_framework.txt](file:05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/fabric_opensource_ai_framework.txt) -- Fabric patterns (separate WO3, not OSINT)
- [Mishaal Khan Resources](https://www.mishaalkhan.com/resources) -- collab confirmation
- [Bombal OSINT YouTube playlist](https://www.youtube.com/playlist?list=PLhfrWIlLOoKPT0y4R_mM4y-2QdfLpAWXl) -- 12-month canon
- [Next Level OSINT (Antisyphon, Khan)](https://www.antisyphontraining.com/product/next-level-osint-with-mishaal-khan/) -- doctrine source

**Word count**: ~770. Not financial or legal advice; legal review recommended before deploying ports 1, 4, 5 in TN/CA/NC/FL given per-state compliance gates.
