# OSINT Tool Teardown — 06_DEVELOPMENT/everlight_os/intel_center/osint_api/
**Date:** 2026-05-15
**Auditor:** Filter Banks + 55_competitive_intel (Lens)
**Scope:** 30 Python modules totaling ~9,115 lines under `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/osint_api/`
**Ground truth:** 36 real investigations on disk; live_log shows 799 domain-pulls, 673 successes (84%).

---

## FAILURES FIRST — what the tool CANNOT do today

1. **Cannot read license plates.** Out by law (DPPA 18 USC §2721). `legal_scope.py:OUT_OF_SCOPE.dppa_dmv` correctly hard-blocks it. There is no path here, ever.
2. **Cannot pull criminal background reports.** FCRA 15 USC §1681 — wholesale outreach is not a "permissible purpose." `legal_scope.py:fcra_consumer_reports` hard-blocks it. We *can* pull court dockets (CourtListener, free, public, non-FCRA) which catches lawsuits/judgments but NOT booking records.
3. **No reverse-username lookup.** social_recon does username -> profile URL probing, but cannot do reverse (profile-photo -> identity, image-search, face-match). Cannot derive a target's social handle from their name alone — we guess `lowercase(name without spaces)`. Hit rate is poor; live_log shows `github.com 404` 12x, `about.me 404` 12x, `youtube.com 404` 15x. Generic name -> wrong-person profiles.
4. **No phone-number lookup with real data.** `skip_trace.py` is URL-generation only — it HEAD-pings TruePeopleSearch / FastPeopleSearch / Spokeo and hands you a clickable link. live_log shows `thatsthem.com 200 (28 successes)` so the link works, but **we extract zero data from the page** because those sites bot-block GETs. We have no Datafiniti / BatchSkipTracing / Endato API integration.
5. **HIBP / Dehashed are link-only.** No API key wired. We send the operator to the page. For breach-confirmation of an email it's dehashed.com 30 successful HEAD probes but no breach data returned.
6. **No image OCR / document parsing inside OSINT.** The parse_assessor_mhtml.py path (114 parsed JSONs) is parallel, not integrated. OSINT investigator output never feeds back into the parcel intel JSON.
7. **`property_records.py` returns only HTTP-status links.** Zillow/Realtor/Redfin/Trulia HEAD-probes. Zero actual price / sqft / listing-history extraction. Stub-tier.
8. **Voice-extractor falls back silently** when an agent's firmware uses unusual formatting. `voice_extractor.load_agent` returns `_default_voice()` on any parse miss — pitch_narrative then uses generic templates without telling you.
9. **`philanthropy_civic._fec` uses `api_key=DEMO_KEY`** which the FEC rate-limits at 30/hr. Real run on "Rich Gee" returned `findings=0` because the demo key was throttled.
10. **`pipeline_smoketest.py` only checks 4 closer agents exist** but the marketing_pipeline STATE_TO_CLOSER maps all 50 states. Most states route to `31_outreach_agent` which is fine but means firmware-level personalization is missing per-state (no real local-flavor pitches outside TN-Marquise / Rust-Belt-Rex).

---

## 1. Module-by-module status table

| # | File | Purpose | Status | Evidence |
|---|------|---------|--------|----------|
| 1 | `investigators/_common.py` | httpx fetch+HEAD with live_log instrumentation, kind detector | **Working** | 799 live_log rows prove it fires. Returns (status, body, err) properly. |
| 2 | `investigators/skip_trace.py` | URL generator for 5 people-finder sites + optional cascade.py fallback | **Stubbed (URL-only)** | HEAD-probes 5 domains; ZERO data extraction. cascade.py wrapper exists at `Wholesale/skip_trace/cascade.py`. |
| 3 | `investigators/social_recon.py` | Sherlock-style 22-platform username probe (HEAD only) | **Working but lossy** | Concurrent HEAD with sem=8. Many platforms return 404 due to bot blocking (github/youtube/about.me/spotify/strava). Real hits: pinterest 51, reddit 37, instagram 37, twitter 13. |
| 4 | `investigators/social_bio_scraper.py` | Full GET on 10 social profile URLs + parses OG tags, JSON-LD, hashtags, bio text | **Working** | Real 204-line module. Regex extractors for `og:description`, JSON-LD `jobTitle/worksFor/address`, hashtags. Test investigation on "Rich Gee" returned 5 findings. |
| 5 | `investigators/public_records.py` | CourtListener API + OpenCorporates + Find-A-Grave HTML + Google News RSS | **Working** | All 4 sub-extractors return real JSON. CourtListener (200), opencorporates.com (200, 10 successes), news.google.com (200, 13 successes), findagrave.com is HTML-scrape (fragile). Caveat: line 159-160 has a dead-code ternary `[:5] if False else ...` that always evaluates the right side — works but should clean up. |
| 6 | `investigators/consumer_signals.py` | Yelp/Goodreads/Letterboxd/Strava/Untappd/Spotify/ProductHunt/IMDb HTTP GETs | **Working but ~50% bot-blocked** | Yelp 403, Strava 404, Untappd 404, Spotify 404 (handle-guessing problem, not module bug). Goodreads + ProductHunt + Letterboxd return 202/200. Same dead-code ternary as public_records lines 80-83. |
| 7 | `investigators/philanthropy_civic.py` | FEC API + ProPublica Nonprofit + GoFundMe HTML + Google Patents | **Half-broken** | FEC uses `api_key=DEMO_KEY` which 429s after ~30 hits/hr (live_log confirms `api.open.fec.gov status=429`). ProPublica + GoFundMe + Patents work. **Real "Rich Gee" run returned 0 findings — FEC was throttled.** |
| 8 | `investigators/property_records.py` | Zillow/Realtor/Redfin/Trulia/Homes.com HEAD probes | **Stubbed (URL-only)** | 32-line file. Zero extraction. Returns HTTP-status as the "finding value." Sellers don't need this — they own the property. We need it for *buyer-side* (Chris) but we have nothing real. |
| 9 | `investigators/leak_check.py` | HIBP domain-breach API + Dehashed/IntelX link generation | **Half-working** | HIBP domain breach query works without auth. HIBP account check requires paid API key — we return a link. Dehashed/IntelX are link-only. |
| 10 | `investigators/google_dorks.py` | DDG HTML search with 6 site-specific dork patterns | **Working** | html.duckduckgo.com 211 successes. Extracts result anchors. |
| 11 | `investigators/domain_intel.py` | crt.sh + urlscan.io + AlienVault OTX + VT/SecurityTrails (HEAD) | **Working** | crt.sh + urlscan + OTX all return real JSON. VT/ST are link-only (no API key). |
| 12 | `investigators/whois_lookup.py` | RDAP Verisign + who.is fallback | **Working** | rdap.verisign.com 200 (7 successes), who.is HTML scrape. |
| 13 | `investigators/archive_org.py` | Wayback availability + archive.org item search | **Working** | archive.org 200 (38 successes). |
| 14 | `investigators/sec_edgar.py` | EDGAR full-text search + tickers JSON catalog | **Working** | sec.gov 200, efts.sec.gov 200. |
| 15 | `investigators/opencorporates.py` | OC v0.4 free-tier company search | **Working** | opencorporates.com 200 (10 successes). Free tier rate-limited per IP but rarely blocks. |
| 16 | `investigators/resource_lookup.py` | Local sqlite query against 745-resource catalog | **Working** | Returns 12 findings per call. No HTTP. |
| 17 | `orchestrator.py` | Async parallel investigator runner + DNC preflight + verification | **Working** | 276 lines. business_purpose enforced. DNC short-circuit via `Wholesale/skip_trace/dnc_check`. SSE event stream. Writes JSON + HTML. |
| 18 | `profile_synthesizer.py` | Buckets findings into Identity/Contact/Online/Property/Business/Risk/Research + builds TLDR + invokes 5-stage pipeline | **Working** | 348 lines. Garbage-finding filter (login-required, 403/404, irrelevant archive items). Calls personality_synth + pitch_hooks + marketing_pipeline + profile_depth. |
| 19 | `personality_synth.py` | Tag findings into 30 interest categories + 11 life-event patterns + comm-style | **Working** | 250 lines. Real regex/keyword matching. Every tag carries source citation. |
| 20 | `pitch_hooks.py` | Generate one-liner hook templates per interest + life-event | **Working (back-compat)** | 239 lines. Now superseded by pitch_narrative for the main pipeline, kept around for legacy callers. |
| 21 | `pitch_tailor.py` | Digest parcel-level intel into seller hook + value-line (investor/absentee/long-hold/tax-delinq) | **Working** | 151 lines. Reads `signals_detected` from parse_assessor JSONs. This is the canonical seller-side personalization. |
| 22 | `marketing_pipeline.py` | 5-stage Profile -> Resonance -> Strategy -> Narrative -> Routing | **Working** | 376 lines. INTEREST_TO_VALUES + LIFE_EVENT_TO_VALUES + POSITIONING_ANGLES (~50 keys). State-to-closer routing for 50 states. NC/IL/CA route to compliance_gate. |
| 23 | `pitch_narrative.py` | Multi-touchpoint email/SMS/voicemail/mail copy by tone + cadence | **Working** | 385 lines. 5 tone packs × 3 touchpoints × 4 channels. Reads agent firmware via voice_extractor for voice override. |
| 24 | `voice_extractor.py` | Parse .claude/agents/<slug>.md into voice dict (openers/signoff/dialect) | **Working but lossy** | 215 lines. lru_cache 64. Returns `_default_voice()` silently on any parse miss — pipeline doesn't know it fell back to generic. |
| 25 | `profile_depth.py` | Score 10 axes 0-100, name gaps, suggest next steps | **Working** | 109 lines. Pure scoring logic. |
| 26 | `report_renderer.py` | Branded gold HTML profile report | **Working (heavy)** | 977 lines. Pure function. State legal panel + watermark + confidence chips. |
| 27 | `legal_scope.py` | IN_SCOPE / OUT_OF_SCOPE static doctrine table | **Working** | 151 lines. Hard-coded but it IS the doctrine — DPPA / FCRA / GLBA / HIPAA / ECPA / minors all blocked. |
| 28 | `legal_state.py` | Per-state channel rules + KNOWN_HARD_BLOCKS (TX/CA/NC/FL/TN/MO/OH/AZ/IL) | **Working** | 264 lines. Reads `Wholesale/compliance/state_gates.json`. lru_cache. Returns `consult Justine` for uncovered states. |
| 29 | `compliance_log.py` | sqlite audit trail of every investigate/view/export/violation | **Working** | 135 lines. compliance.sqlite written by every action via main.py. |
| 30 | `live_log.py` | Per-domain success/failure trail (last status, success_count) | **Working** | 135 lines. 799 rows live. |
| 31 | `investigation_store.py` | sqlite + JSON-on-disk persistence | **Working** | 36 investigations on disk. |
| 32 | `main.py` | FastAPI app, port 8677, SSE `/events`, branded `/report/{id}` | **Working** | 159 lines. business_purpose enforced at HTTP layer. template_lint runs at startup. |
| 33 | `template_lint.py` | Startup-time scan of POSITIONING_ANGLES + BODY_TEMPLATES against pre_send_phrase_scrub baseline | **Working** | Aborts app boot on violation. |
| 34 | `pipeline_smoketest.py` | Walk 50 states, assert STATE_TO_CLOSER + agent file + parseable voice | **Working** | Run standalone. |
| 35 | `domain_status.py` | Classify each domain live/auth_gated/dead/rate_limited | **Working** | Reads live_log. |
| 36 | `public_url.py` | Env-driven public hostname (esign/reports/hub) | **Working** | 76 lines. Falls back to 127.0.0.1 — public host not yet set. |
| 37 | `arc_send.py` | 3-round seller arc + 3-round buyer arc email orchestrator | **Working (out of scope for OSINT)** | 778 lines. Belongs to outbound pipeline, not OSINT. Listed for completeness. |
| 38 | `contract_renderer.py` | Render 5 deal contract HTMLs from deal_meta | **Working (out of OSINT scope)** | 522 lines. Same. |
| 39 | `esign_server.py` | Self-hosted UETA/E-SIGN signing server on port 2302 | **Working (out of OSINT scope)** | 1179 lines. Same. |
| 40 | `signature_burner.py` + `pdf_certificate.py` | Burn sig into HTML + generate cert PDF | **Working (out of OSINT scope)** | 220 + 200 lines. Same. |

---

## 2. Capability Map — Sellers + Buyers

### What we CAN do today (seller pitch — TN/TX/FL/GA/OH/AZ/MO/NV)

| Capability | Source | Status |
|---|---|---|
| Owner name + mailing address + sales history + appraisal value + build year + LLC detection + absentee detection + tax delinquency + multi-deed pattern | `parse_assessor_mhtml.py` -> 114 parsed JSONs | YES, primary path |
| Personalized opener (investor / absentee / long-hold / tax-delinq / fallback) | `pitch_tailor.tailor_for_seller` | YES |
| Per-state legal gating (channels allowed, hard blocks, citations) | `legal_state.state_rules_for` + `state_gates.json` | YES |
| Court docket / lawsuit / opinion history | `public_records._courtlistener` (free API) | YES |
| Business filings / officer roles | `public_records._opencorporates` + `opencorporates.py` + `sec_edgar.py` | YES |
| Public obituary / death record | `public_records._findagrave` | Fragile (HTML scrape) |
| News mentions of the owner | `public_records._news_archive` (Google News RSS) | YES |
| Public social bios + hashtags + job title + location | `social_bio_scraper` | YES, but only when handle is guessable |
| Username sweep across 22 platforms | `social_recon` | HEAD-only, ~50% bot-blocked |
| Public consumer behavior (Yelp/Goodreads/Letterboxd/Spotify/etc.) | `consumer_signals` | YES, ~50% blocked |
| Public political donations | `philanthropy_civic._fec` | BROKEN (DEMO_KEY 429s) |
| Public 501c3 board membership | `philanthropy_civic._propublica_nonprofit` | YES |
| Public patents | `philanthropy_civic._patents` | YES |
| Email-breach history | `leak_check` (HIBP domain only) | Partial |
| Personality synthesis (30 interests / 11 life events / comm style) | `personality_synth.synthesize_personality` | YES |
| Multi-touchpoint pitch (email/SMS/VM/mail × 3 touches × 5 tones) | `pitch_narrative.build_narrative` | YES |
| Voice-matched outreach by agent firmware | `voice_extractor.load_agent` | YES but silently falls back to default |
| DNC preflight | `Wholesale/skip_trace/dnc_check` (via orchestrator) | YES |
| Identity verification per finding (state/city/email/phone match) | `Wholesale/skip_trace/identity_verifier` (via orchestrator) | YES |
| Compliance audit trail | `compliance_log` | YES |

### What we CAN'T do, ranked by wholesale-pipeline ROI

| # | Missing capability | Tool/method | Free/paid | Effort | Creep-line | Wholesale ROI |
|---|---|---|---|---|---|---|
| A | Real phone-tied skip-trace (number -> name+address verified) | Endato / BatchSkipTracing / Datafiniti API | Paid ($0.10-0.25 / lookup) | S | green | HIGH — closes the "we have a mailing addr, need a phone" gap. Today we link to TruePeopleSearch and the operator clicks. |
| B | Owner email discovery | Hunter.io / Snov / Apollo / Clearbit (deprecated free tier) | Paid ($49-99/mo) | S | green | HIGH — email is our HARD-LAW primary channel. Without an email we can't fire. |
| C | LinkedIn public profile pull | Phantombuster / PhantomBuster / Bright Data residential | Paid ($30-90/mo) | M | yellow | HIGH — job title + employer is the strongest personality signal. social_bio_scraper hits LinkedIn 401 today. |
| D | Reverse-image / face-match on profile photos | Pimeyes (paid) / TinEye API / facecheck.id | Paid ($30/mo) | M | RED | LOW — too creepy, violates Google-test |
| E | Real-time obituary alerts | Tributes.com / Legacy.com RSS / Newspapers.com | Mostly free (RSS) | S | green | MEDIUM — recently_widowed is one of our strongest pitch signals |
| F | Foreclosure-notice scraper per state | County clerk websites / RealtyTrac | Free if scraped / paid otherwise | L | green | HIGH — this is THE wholesale signal but requires per-state scraper |
| G | Bankruptcy filing lookup (PACER) | PACER free RECAP search | Free (CourtListener already has RECAP) | S | green | MEDIUM — already partially via CourtListener but needs explicit BK form filter |
| H | Sherlock (full real tool) instead of our HEAD-shim | https://github.com/sherlock-project/sherlock (300+ sites, GET-based) | Free, OSS | M | green | MEDIUM — wider coverage than our 22 platforms, smarter false-positive filtering |
| I | Holehe (email -> account existence on 120+ sites) | https://github.com/megadose/holehe | Free, OSS | S | green | MEDIUM — lets us validate an email + reveal social handles |
| J | Maigret (improved Sherlock with profile parsing) | https://github.com/soxoj/maigret | Free, OSS | M | green | MEDIUM — replaces our hand-rolled social_recon + social_bio_scraper with proven tooling |
| K | License plate -> owner | DMV / Carfax / various commercial | Paid + ILLEGAL for cold outreach | — | RED HARD STOP | DPPA blocks. Don't build. |
| L | Criminal background report | TLO / IRB / IntelTechniques tools | Paid + FCRA blocks for wholesale | — | RED HARD STOP | Wholesale is not a permissible purpose. Don't build. |
| M | Image OCR of MHT/PDF parcel docs (already in workflow but not OSINT) | tesseract or `mhtml-parser` extension | Free | S | green | MEDIUM — only matters if owners upload docs |
| N | Property comp data (for buyer-Chris vetting) | RentCast API / ATTOM Data / Redfin scrape | Paid ($49-99/mo) | M | green | HIGH — `property_records.py` is currently a stub. This is the missing piece for buyer side. |
| O | OFAC SDN check (for Inner Circle buyer vetting) | Treasury OFAC SDN list (free CSV download, daily) | Free | S | green | HIGH — required for Open Deal Inner Circle, currently no module touches OFAC |
| P | Stripe Identity verification (for Inner Circle) | Stripe Identity API | Paid ($1.50/check) | S | green | HIGH — same as above |

---

## 3. Top 7 gaps ranked by Deal-1 -> Deal-100 impact

### Gap 1 — Email Discovery for Owners (HIGH urgency, S effort)
**Today:** 61 of 114 parsed parcels have a mailing address. ZERO have an email. We are digital-only by HARD LAW, so without an email we cannot fire. The pipeline is currently silently truncated.
**Build:** Add `investigators/email_discovery.py`. Use Hunter.io free tier (50/mo) + clearout.io (100 free verifications) + email permutation heuristic (`firstname.lastname@`, `f.lastname@`, `firstinitial+lastname@`) cross-checked against MX records. Snov.io for the rest at $39/mo. Free path first: Hunter + permutation + DNS MX gives ~30% coverage at $0/mo. After Deal-1, add Snov for the long tail.
**Wholesale ROI:** Without this we can't email 53 of 114 parsed leads. Direct revenue gate.

### Gap 2 — FEC DEMO_KEY swap-out (HIGH urgency, S effort)
**Today:** `philanthropy_civic._fec` uses `api_key=DEMO_KEY` which 429s after 30 req/hr. live_log confirms `api.open.fec.gov status=429`. The "Rich Gee" investigation returned 0 FEC findings because of throttling.
**Build:** Free FEC personal API key (https://api.open.fec.gov/developers/) — registration takes 60 seconds. Store in env `FEC_API_KEY`. Update `philanthropy_civic.py` line 37.
**Wholesale ROI:** Political donations are one of our strongest personality signals — they reveal civic values, donor capacity, sometimes age + city verification.

### Gap 3 — Replace `social_recon` HEAD-probe shim with Maigret (HIGH urgency, M effort)
**Today:** Our hand-rolled social_recon HEADs 22 platforms. About half return 404 due to bot-blocking (`github.com 404`, `youtube.com 404`, `about.me 404`, `spotify 404`, `strava 404`). Sherlock and Maigret are open-source, GET-based, handle false positives by parsing page content, support 300+ sites.
**Build:** `pip install maigret`, wrap as `investigators/maigret_sweep.py`. Run async subprocess with 30s timeout. Parse maigret's JSON output. Keep our social_bio_scraper for the deep-fetch step.
**Wholesale ROI:** Social handle discovery quality directly drives whether social_bio_scraper has any data to mine, which drives personality_synth quality.

### Gap 4 — License Plate (Rich asked about it) — HARD NO, document why (HIGH visibility, S effort)
**Today:** Rich mentioned wanting license-plate lookup. Out per DPPA (18 USC §2721) — civil + criminal penalties. `legal_scope.py:OUT_OF_SCOPE.dppa_dmv` already documents this.
**Build:** Don't. Add a `legal_scope.explain_block(category)` helper that surfaces the statute citation in the report, so when an operator asks "why isn't plate lookup here?" the report shows the answer inline. Update `report_renderer.py` to add a "Why these capabilities aren't included" section listing the 5 hard-blocked classes with citations.
**Wholesale ROI:** Zero direct, but high coaching ROI — Rich, Marquise, and future hires need this written into the tool so the team stops asking.

### Gap 5 — Criminal Background (Rich asked) — HARD NO, but offer the *legal* substitute (HIGH visibility, S effort)
**Today:** FCRA blocks consumer-report background reports for wholesale outreach (15 USC §1681). We CAN read public court records (CourtListener) which catches lawsuits, judgments, bankruptcies, evictions.
**Build:** Beef up `public_records._courtlistener` to add a "Bankruptcy / Eviction / Judgment" filter (RECAP supports BK case search). Surface this in the report under "Risk Signals" as "public court appearances" — never as "criminal record." Same data, lawful framing.
**Wholesale ROI:** Eviction history is a strong distress signal. Judgment history correlates with motivated sellers.

### Gap 6 — Holehe Email Existence Check (MEDIUM, S effort)
**Today:** When we have an email but no name, we have nothing. Holehe checks 120+ sites to see where an email has an account — by extension, where to look for that person's public bio.
**Build:** `pip install holehe`, wrap as `investigators/holehe_check.py`. WHEN=`["email"]`. Output: list of sites where the email has an account. Feed those handles into social_bio_scraper for deep-mine.
**Wholesale ROI:** Buyer-side vetting (Chris-like): "this Inner Circle applicant's email has accounts at Stripe + LinkedIn + GitHub" is a confidence-builder. Sellers usually don't give us email until later in the arc, so seller-side ROI is lower.

### Gap 7 — Property comps for buyer-side (BUILD-OUT, M effort)
**Today:** `property_records.py` is a 32-line URL-generator stub. For Open Deal Inner Circle ($99 + 10% walk fee) buyers like Chris, we need to vet that the deal we're handing them actually has ARV math. Zillow/Redfin block scrapers; RentCast has a free tier (50 calls/mo).
**Build:** Replace property_records.py with RentCast integration + ATTOM Data trial. Output should include ARV estimate, rent estimate, last sale price, sqft, condition. WHEN=`["address"]`. This becomes the back-end of buyer-side `pitch_tailor.tailor_for_buyer` (currently a stub at pitch_tailor.py:141-151).
**Wholesale ROI:** Higher buyer trust = higher Inner Circle conversion = recurring $99/mo MRR. First deal funds this.

---

## 4. The "Google version" test — applied to each proposed add

| Capability | Would Google use this signal? | Would Google reveal where they got it? | Verdict |
|---|---|---|---|
| Email discovery (Hunter + permutation) | YES (Gmail knows your contacts) | NO (Gmail never says "we got your address from Hunter") | GREEN |
| FEC donor history | YES (Google News indexes FEC pages) | NO (search results show the article, not the FEC query) | GREEN |
| Maigret social sweep | YES (knowledge panel pulls public bios) | NO (just shows the bio, not the crawler path) | GREEN |
| LinkedIn public profile pull | YES (Google indexes LinkedIn public pages) | NO | GREEN with caveat — never paste the LinkedIn URL into the email body |
| Court records (CourtListener) | YES (PACER mirror in Google Scholar) | NO | GREEN |
| Patent search | YES | NO | GREEN |
| Public obituaries | YES | NO | GREEN |
| Property comps (RentCast/ATTOM) | YES (Google maps real-estate panel) | NO | GREEN |
| OFAC SDN check | YES (compliance signal, never disclosed) | NO | GREEN |
| License plate lookup | NO (Google doesn't, DPPA blocks it) | N/A | RED — don't build |
| Criminal background report | NO (Google doesn't serve FCRA data) | N/A | RED — don't build |
| Face match / reverse image | NO (Google Lens does it for OBJECTS, never for people) | N/A | RED — too creepy |
| Phone-tied skip-trace | YES (Google contacts feature) | NO | GREEN with caveat — only use signal to verify, never quote |

**The doctrine:** signal lives in the pipeline; surface lives in the language. Pitch says "We work with multi-property owners like yourself" not "We saw you own 3 LLCs at OpenCorporates." The discriminator is INVISIBLE; the relevance is FELT.

---

## 5. What to delete or shelf

### Delete (dead code / overlap)
- `investigators/public_records.py:159` and `investigators/consumer_signals.py:80-83` — dead-code ternary `[:5] if False else list(...)[:5]`. Cosmetic; works but should be cleaned.
- `pitch_hooks.py` — superseded by `pitch_narrative.py` + `marketing_pipeline.py`. Currently kept as legacy. Once nothing imports it (grep first), retire it to `_legacy/`.
- `pitch_tailor.tailor_for_buyer` (lines 141-151) — stub returns a hardcoded one-liner. Either build it out as part of Gap 7 or remove and let the buyer flow live in `arc_send`.

### Shelf (move out of osint_api/ — wrong neighborhood)
- `arc_send.py` (778 lines) — outbound email orchestrator. Belongs in `Wholesale/outbound/` or `03_AUTOMATION_CORE/01_Scripts/outreach/`.
- `contract_renderer.py` (522 lines) — deal-doc rendering. Belongs in `Wholesale/contracts/`.
- `esign_server.py` (1179 lines) — separate FastAPI service on port 2302. Belongs in `03_AUTOMATION_CORE/services/esign/`.
- `signature_burner.py` + `pdf_certificate.py` — same neighborhood as esign.
- Rationale: `osint_api/` should mean "investigators + synthesizers + reporters." Mixing the deal-execution layer in here makes the directory confusing for new operators and dilutes the OSINT mission.

### Security risk
- `esign_server.py:42` — `ESIGN_SECRET = os.environ.get("ESIGN_SECRET", "everlight_esign_dev_secret_change_in_prod")` falls back to a hardcoded dev secret. Anyone who reads the source can forge sign tokens. **HIGH priority: require env var, abort startup if missing in prod mode.**
- `compliance_log.py` and `live_log.py` — both write to sqlite in `cache/` with default world-readable perms. Investigations contain owner names + addresses. **Add `os.chmod(0o600)` on creation** (orchestrator.py already does this for the JSON files at line 213, do same for the .sqlite files).
- `public_url.py` falls back to `127.0.0.1` — fine for dev. Once we set `EVERLIGHT_PUBLIC_HOST`, audit every place that constructs URLs to ensure no hardcoded `127.0.0.1` slips through.

---

## Bottom line for Rich

**The tool is real, not a demo.** 36 investigations on disk, 673 successful domain pulls, 9,115 lines of working code. The Apple-Store-of-Wholesaling bar is achievable from here, but you're missing 3 things that gate Deal-1 -> Deal-100:

1. **Email discovery** (no email = no fire under digital-only HARD LAW). 53 of 114 parsed parcels are dark.
2. **FEC DEMO_KEY** (free registration, 60-second fix, instantly unblocks one of the strongest personality signals).
3. **Maigret instead of our HEAD-shim** for social sweep (free OSS, replaces ~half-broken social_recon).

The three things Rich asked about specifically:
- **License plates:** NO. DPPA. Don't build.
- **Criminal background:** NO as "criminal background." YES as "public court appearances" (CourtListener already wired, beef up the BK/eviction filter).
- **Social media usernames:** YES. Sherlock/Maigret/Holehe deepen what we already have. Build Gap 3 + Gap 6.

Everything else (face match, reverse image, phone-tied skip-trace, property comps) is post-Deal-1 unlock unless it gates the micro path.

**Files referenced:**
- `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/osint_api/` (30 modules, 9,115 lines)
- `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/investigations/` (36 real investigations)
- `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/cache/live_log.sqlite` (799 domain pulls, 84% success)
- `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed/` (114 parsed parcels)
- `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/state_gates.json` (compliance source of truth)
