# AroundMe: Project Handoff

**What it is:** a single-operator, free-stack live-safety map that fuses ~18 public feeds (CHP, 511, NWS, USGS, scanner + Whisper, ADS-B, mesh, social) into one incident view with threat scoring, a shelter-vs-evacuate decision engine, and smart multi-route escape routing.

**Date:** 2026-07-12

---

## Bottom line

AroundMe today is a genuinely working personal safety desk for one operator, not the multi-user consumer product the 16-week vision describes. The fusion engine, threat matrix, incident lifecycle, decision engine, and single-user escape routing are real and tested; but the headline consumer promises are mostly unbuilt or overstated. Blunt version: there is no native app, no accounts, no billing, and no Stripe (so zero of the monetization exists); the "SOS emergency contact" fires to one shared ntfy topic and silently no-ops if an env var is unset; crash detection only runs while a browser tab is foreground; "siren detection ML" and "RTL-SDR nodes" are vaporware with zero code; and the "legal reframe" only hides risk-scores and person/plate extraction in the React tree while the FastAPI backend still computes and serves them on open JSON endpoints. Across all seven areas: 14 features DONE, 22 PARTIAL, 25 PLANNED.

---

## Reality check on the handoff doc

The source vision doc assumes a **Firebase + Mapbox + parallel-pipeline** stack. We do not use any of that. Every recommendation has to be re-mapped onto what actually ships:

| Vision doc assumes | Our real stack |
| --- | --- |
| Firebase / cloud DB | Python **FastAPI** + **per-day SQLite** event store (`sld/store.py`), single global store, no user dimension |
| Mapbox / Google Maps | **MapLibre GL** (`console/components/MapView.tsx`) |
| Mapbox Directions | Free **OSRM** + **OpenStreetMap Overpass** (`sld/routing.py`, `sld/escape.py`), no avoid-polygon |
| Managed hosting | Free **Oracle ARM VM ("e5")** running one `solano-desk.service` unit |
| Multi-user app w/ accounts | **Single operator**, one `SLD_ACCESS_TOKEN` magic-link cookie gate, no accounts |
| React Native / Firebase push | **Next.js 14 static export** (`output: 'export'`) served by FastAPI; push via free **ntfy** |

Practical consequence: anything the vision routes through Firebase Auth, Firestore, or Mapbox has to be re-planned for Supabase Auth (for accounts), SQLite/Postgres, OSRM/Valhalla, and ntfy. The good news is the free-first stack already covers nearly everything except the one $25 Google Play registration.

---

## Status by area

Status values are verbatim from the audit: **DONE** / **PARTIAL** / **PLANNED**.

### 1. Native app + Google Play packaging

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Capacitor wrap of web app into Android app | PLANNED | No `capacitor.config.*`, no `android/`/`ios/`, no `@capacitor` deps; `grep -rli capacitor` hits only `docs/AROUNDME_PIVOT.md` | Scaffold Capacitor against the Next static export (`webDir` -> `console/out`), add `capacitor.config.ts`, `npx cap add android` |
| Google Play packaging ($25 one-time) | PLANNED | No `*.aab/*.apk/*.keystore/*.gradle/AndroidManifest.xml` in repo | After `android/` exists: signing keystore, `applicationId`, signed `.aab`, register $25 Play Console, data-safety form (location + accelerometer, on-device) |
| Web-to-app static-export foundation | PARTIAL | `console/next.config.mjs` sets `output:'export'`, `basePath/assetPrefix '/console'`, `images.unoptimized`, `trailingSlash` | Prereq DONE; note `basePath:'/console'` breaks a bundle-root native load: drop basePath for native or point `capacitor.config server.url` at e5 |
| Background GPS in the app | PARTIAL | `scripts/gps_beacon.sh` termux daemon + browser beacon (commit 189856b); no native BackgroundGeolocation plugin | Add Capacitor background-geolocation plugin POSTing the same beacon payload FastAPI already accepts |
| Push notifications in the app | PARTIAL | ntfy push live (`/api/sos`, `CrashGuard.tsx`); no FCM/APNs native code | Free-first: keep ntfy topic, wrap via ntfy UnifiedPush; avoid Google FCM entirely |
| Splash screen | PLANNED | No splash assets/config; only an apple-touch-icon in old `web/index.html` | After `android/`: `@capacitor/splash-screen` + real PNG launcher/adaptive icons (the lone `icon.svg` is not a valid Android launcher asset) |
| Audio ducking plugin | PLANNED | No ducking code; the TTS station it would duck is itself unbuilt | Deferred; last item, downstream of the unbuilt audio station |
| iOS add-to-home / App Store later ($99/yr) | PARTIAL | `layout.tsx` `appleWebApp{capable, black-translucent, title 'AroundMe'}` + `viewportFit:'cover'`; no Xcode project | iOS install limited to Safari "Add to Home Screen" today; `npx cap add ios` after Android ships |
| Installable PWA manifest | PARTIAL | `web/manifest.json` STALE (name "Solano Live Desk" / short_name "Survival OS", single SVG icon); `KillSW.tsx` unregisters all service workers + purges caches on load | Add manifest link to `layout.tsx`, rename to AroundMe, ship PNG maskable icons; decide KillSW tradeoff (blocks offline PWA) via versioned SW or Capacitor bundle |

### 2. Personal-safety features

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Reckless-driver report (one-tap) | DONE | `reports.py add_report()` + 5 reckless KINDS; `POST /api/report`; `ReportPanel.tsx` buttons; markers in `MapView.tsx` | Optional: server-side dedupe of near-duplicate reports |
| Reckless report (voice) | PLANNED | No `SpeechRecognition`/`getUserMedia` anywhere; ReportPanel is tap-only | Add browser Web Speech API in `ReportPanel.tsx` -> map phrase to KINDS key -> reuse `postReport()` |
| Time-decaying markers | DONE | KINDS ttl (reckless 900s, hazard 3600s, pothole 86400s); `active()` purges expired, returns `ttl_s`/`age_s` | Optional: fade marker opacity by `ttl_s` |
| Warns drivers, not police | DONE | Module/docstrings + ReportPanel footer "Reports warn other drivers, not law enforcement"; no 911 wiring on report path | Working as designed |
| Severity escalation | PARTIAL | Static per-kind tiers (wrongway CRITICAL, etc.); no dynamic escalation from repeat reports | In `active()`, count same-kind reports within ~150m/10min and bump returned severity (read-side only) |
| SOS / panic (share location + dial 911) | DONE | `POST /api/sos` builds maps link + fires `ntfy_sender` priority 5; `CrashGuard.tsx` SOS + `tel:911` + maps link | Real but **single-recipient**: pushes one shared `SLD_NTFY_URL`, `ok:false` if unset. Add per-operator ntfy topic in localStorage passed to `/api/sos` |
| Crash detection (accelerometer auto-SOS) | PARTIAL | `CrashGuard.tsx` devicemotion, `CRASH_MS2=29` (~3g), iOS permission gate; fires `sendSos(kind='crash')` | Foreground-tab only; background sensor needs the unbuilt Capacitor shell. Keep foreground; document limit in-app |
| Crash detection (cancelable countdown) | DONE | `CrashGuard.tsx` 12s countdown overlay + "I'M OK" + "Send now"; auto-fires at 0 | Working |
| Gig-driver "on delivery" self-marking | DONE | `mark_presence()/clear_presence()` (ttl 300s upsert); `POST /api/presence`; ReportPanel toggle refresh 60s; truck icon in MapView | Working; client id is a localStorage random string (fine single-op, needs real accounts multi-user) |
| Siren detection via phone-mic ML (YAMNet/TFLite) | PLANNED | No siren/yamnet/tflite/mic code; "siren" only appears as scanner text-parse in `radio.py` | Load YAMNet as TF.js in browser behind a mic-permission gate; drop local advisory marker on hit (pure front-end) |

### 3. Navigation + routing

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Multi-route escape ranking (lights + stops as time cost) | DONE | `escape.py plan_escape()/score_route()` (`SIGNAL_PENALTY_S=18`, `STOP_PENALTY_S=7` via Overpass); `/api/escape`; ranked routes in MapView + WAYS OUT panel; `test_escape.py` 9/9 | Solid. Tune penalties (OSRM base duration already models signals) or measure vs real drive times |
| Speed limits as time cost | PARTIAL | Uses OSRM per-class DEFAULT speeds, not posted limits; no `maxspeed` query | Add `maxspeed` to `escape._fetch_controls` Overpass query; adjust base_duration per-segment |
| Avoid incident-blocked roads | PARTIAL | `_blockers()` collects hazard POINTS only; `BLOCK_PENALTY_S=3600` ranks blocked route LAST but still returns it; "No avoid-polygon" (`routing.py:5`) | Self-host Valhalla for real exclude_polygons, or waypoint-offset re-request; feed evac-ORDER polygons into blocker set |
| Disperse traffic system-optimally (coordinated egress) | PLANNED | `escape.py` docstring: "This is the single-user version"; no multi-user backend | Blocked on accounts plane; then server-side assignment loop handing adjacent operators different top-N routes |
| Route-intersection alerts (only incidents ON the route) | PARTIAL | `score_route()`/`_near_line()` compute on-route hazards at plan time; but live alerting is threat + proximity-to-USER, not route-based | Persist chosen route geometry, run each new incident through `_near_line` in `alert_worker`, push only on true on-route hit |
| Turn-by-turn navigation | PLANNED | OSRM called without `steps=true`; no maneuver parsing; MapView draws a plain line | Add `steps=true`, parse `legs[].steps[].maneuver` into `/api/escape` + `/api/route`, render step list |
| Auto-reroute | PLANNED | `/api/escape` is one-shot on EVACUATE click; no polling/GPS re-fetch | Hook background GPS beacon + incident feed; re-call `getEscape` on drift or new blocker; diff-and-replace |
| Gig multi-stop optimization | PLANNED | Only a gig presence MARKER; no trip/table/waypoint/optimize code | Add `/api/trip` POSTing to free OSRM `/trip/v1`, return optimized leg order + geometry |

### 4. Audio "commuter news station"

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| TTS voice alerts | PARTIAL | Legacy only: `web/app.js` `speechSynthesis.speak()` on a button; shipped Next console has NO speechSynthesis (web/ superseded by /console/) | Port Web Speech API into `console/app/page.tsx`: add `speak(text)`, trigger in the fresh-critical-incident effect that currently only calls `playBeep()` |
| 5 alert channels (My Route/My Zone/Weather/Gig Intel/Commuter Brief) | PLANNED | No channel/topic tokens; `muted` is a single global boolean | Model channels client-side: `Record<channel,bool>` mute map keyed off existing data; "Commuter Brief" = FastAPI endpoint concatenating top-N fused incidents |
| Audio ducking (lower Spotify, speak, restore) | PLANNED | No duck/audiofocus code; a browser tab cannot lower another app's audio | Blocked on native wrapper (Android `AudioManager`); interim MediaSession API for lock-screen controls |
| Earcons | PARTIAL | Exactly one: `playBeep()` (880->620Hz) on fresh critical incident; no per-channel set | Extend `playBeep()` into an earcon table driven by `threat.py` level (client-side WebAudio) |
| Voice-activated reporting | PLANNED | No `SpeechRecognition` in console/web/sld | Add mic button in `ReportPanel.tsx` via browser SpeechRecognition -> POST to existing `/api/report` |
| Constraints (max 8s, action-first, no repeats within 5 min) | PLANNED | No cap/cooldown; `playBeep()` fires per poll batch, gated only by global mute | When TTS lands, add `spokenRecently Map<id,ts>` (300s suppress) + truncate to ~140 chars |

### 5. Weather integration

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| NWS severe-weather alerts as polygons | PARTIAL | `nws.py parse_alerts()` collapses geometry to ONE centroid; `store.py` has no geometry column; rendered as a single dot | Add `geom TEXT` column via `_MIGRATIONS`; carry raw feature geometry; feed MapView's existing danger-fill Polygon layer |
| Route/polygon intersection | PLANNED | Point-in-ring math exists (`decide._point_in_ring`) but only tests operator-in-evac-zone; weather never reaches blocker set (`threat.severity` has no flood/storm keywords) | After polygons stored, add polygon-vs-polyline test reusing `_point_in_ring`, flag routes crossing an NWS polygon via existing blocked/avoids plumbing |
| Storm tracking (direction + speed -> time to intersect) | PLANNED | No storm/track/velocity code; `nws.py` ignores `properties.parameters` | Parse `eventMotionDescription`/VTEC bearing+speed; add projection helper advancing polygon; compute minutes-to-intersect |
| Best-driving-times suggestion | PLANNED | Only active-alerts endpoint pulled; no gridpoint/forecast call | Add free `api.weather.gov` hourly forecast fetch + scorer ranking next N hours; new `GET /api/weather/best-times` |

### 6. Scanner, siren detection, mesh

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Broadcastify scanner ingest + Whisper transcription | DONE | `broadcastify.py` + `transcribe.py` (faster-whisper VAD) + `scanner_pipeline.py` (download->transcribe->code-name->geocode->store); `/api/scanner_audio` + `/api/feeds` | **Pin `faster-whisper` in requirements.txt (missing)** and commit the referenced `scanner.timer` unit -- it does not exist, only `solano-desk.service`, so scheduled transcription is not deployed |
| Siren detection ML on phone mic | PLANNED | No siren-mic code; `AudioContext` is an OUTPUT beep, not mic input | Add browser MediaRecorder mic capture, POST clips to new `/api/siren`, run YAMNet/tflite on e5, emit advisory marker |
| Meshtastic off-grid mesh | PARTIAL | `meshtastic_mesh.py` (MQTT subscribe, AES-CTR decrypt, writes mesh.json); READ-ONLY, internet-MQTT dependent, not true off-grid | **Add meshtastic + paho-mqtt + cryptography to requirements.txt (all missing)** + committed mesh systemd service; add outbound beacon + serial/LoRa path |
| Crowdsourced confirmation ("I hear it too") | PARTIAL | MACHINE fusion only (`correlate.py` UNCONFIRMED/PROBABLE/CONFIRMED); no human confirm endpoint; single-operator | Add `/api/confirm?incident_id` + a confirm button in `DetailDrawer.tsx` feeding correlate confidence; real value gated on multi-user backend |
| RTL-SDR power-user nodes | PLANNED | Zero rtl-sdr/rtl_fm/sdr/op25 hits | Define `/api/sdr_node` ingest of call metadata + audio from volunteer boxes, route through existing transcribe + geocode/store path |

### 7. Fused incident data pipeline

| Feature | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Scanner + transit + flights + shelters FUSED | PARTIAL | Only `ingest.py` (CHP/NWS/quakes/FIRMS/roads) + `scanner_pipeline.py` call `upsert_event`; transit/aircraft/trains/evac/fema never do; of the 4 named sources only scanner is fused | Add `run_once_transit/aircraft/trains` in `ingest.py` normalizing to event dicts, route through `_store_all`/`upsert_event` |
| ~18 fused free feeds | PARTIAL | ~18 feed modules exist but only 6 write to the events store; rest are isolated overlays | Decide per feed: incident (route into store) vs ambient context (overlay); wire incident-class feeds into `poll_loop` |
| Dedup across sources | DONE | `correlate.py` union-find `_cluster`/`_linked` (30-min window + shared unit or <=0.3mi or shared code within 1.5mi) + confidence tiers | Quality jumps once missing feeds enter the store |
| Geocode | DONE | `chp_parser.decode_latlon`; scanner geocodes with cached budget; nws/quakes/firms/roads native lat/lon | Add fallback geocode (Nominatim/Overpass) for ungeocoded events, or log the silent `lat is None` drops |
| Classify by type | PARTIAL | Type is free text carried from each source; no unified taxonomy | Add `classify_type()` in `threat.py` mapping CHP/scanner/511 vocab to a fixed enum, applied in `_store_all` |
| Severity 1-10 | PARTIAL | Severity is a 4-tier keyword string (CRITICAL/HIGH/MEDIUM/LOW), not numeric 1-10 | If 1-10 wanted, add numeric `score()` from tier + proximity ring + source-count; keep the working 4-tier |
| Geofence | DONE | `RADIUS_MI=45` bubble around live GPS; `chp_parser` distance filter; proximity rings; per-feed `near()` radii | None; solid |
| Time decay | DONE | `store.on_day` daily reset; `lifecycle_status` LIVE<=15min; auto-close at 180min | Optional: continuous recency weight in fusion confidence |
| Incident lifecycle | DONE | `correlate.lifecycle()` ACTIVE/ONGOING/WINDING DOWN/CLEARED/CLOSED from clear-codes + activity + staleness; DVR cross-day log; `/api/incidents` | None; strongest part of the area (derived-not-dispatched caveat honestly documented) |
| Flight passenger counts | PARTIAL | `_TYPE_SEATS` + 0.83 load factor `est_pax` on `/api/flight` overlay, labeled an estimate; lives on overlay not fused store | If pax should influence severity, emit ADS-B emergency squawks as events with `est_pax` via `run_once_aircraft` |
| Shelters (FEMA/OSM) fused | PARTIAL | `evac.py` Overpass shelters/hospitals/police/fire (`/api/safe`) + `fema.py` (`/api/fema`) feed decide.py + routing destinations, not the events store | Correct if shelters are destinations; if FEMA declarations should show as context, add `run_once_fema` upserting low-severity area events |

---

## Shipped this session (2026-07-12)

Newly-live, verified against code:

- **Dispersed Egress smart-escape** -- `escape.py` + `/api/escape`, ranks OSRM alternatives by real free-flow time (18s/traffic-light, 7s/stop-sign penalties), drops incident-blocked roads; `test_escape.py` 9/9 pass. Honestly labeled "the single-user version" in its own docstring.
- **Crash detection + SOS** -- `CrashGuard.tsx` (~3g devicemotion threshold, iOS permission gate, 12s cancelable countdown) + `/api/sos` firing max-priority ntfy push and a `tel:911` + maps-link handoff.
- **Reckless-driver + hazard reports** -- `reports.py` + `/api/report` + `ReportPanel.tsx`, seven time-decaying kinds (reckless 900s / hazard 3600s / pothole 86400s), "warns drivers, not police" framing.
- **Gig-driver "on delivery" self-marking** -- `mark_presence()/clear_presence()` + `/api/presence`, 300s upsert, truck marker, 60s refresh.
- **Daily-reset fix** -- `store.on_day` drops yesterday's stragglers so the queue and map start clean each day.
- **AroundMe rename + install meta** -- `layout.tsx` `appleWebApp{capable, black-translucent, title 'AroundMe'}` + `viewportFit:'cover'` for iOS add-to-home fullscreen.
- **Legal-reframe build flag** -- `lib/mode.ts` `PUBLIC_BUILD` (`NEXT_PUBLIC_AROUNDME_MODE=public`) dead-code-eliminates risk-score + entity-extraction UI in the public build. **Caveat: front-end only -- the FastAPI backend still computes and serves that data on open JSON endpoints.**
- Also live: background GPS beacon (commit 189856b) and the ntfy push channel.

---

## The real next 5 moves

Prioritized, on our actual free stack. Exactly one step costs money.

1. **Make redeploy not silently break (free).** Pin `faster-whisper`, `meshtastic`, `paho-mqtt`, `cryptography` in `requirements.txt` (all missing) and commit the `scanner.timer` + a mesh systemd unit the code already references. Right now a clean redeploy would fail to start scanner transcription and mesh. This is the cheapest, highest-leverage fix.
2. **Close the legal-reframe hole server-side (free).** Add the `AROUNDME_MODE` flag to `sld/config.py` and strip `risk_score`/`risk_level`/`risk_factors`/`entities` out of the FastAPI JSON in the public deployment. Today any client hitting the open endpoints gets the full person/plate/risk data the UI merely hides -- the exact FHA/defamation exposure counsel flagged.
3. **Stand up accounts (free, Supabase Auth).** This is the single blocker for coordinated egress, per-user SOS contacts, pricing tiers, billing, and crowd confirmation. Add per-user location/plan rows; enforce feature access in FastAPI dependencies, not the client bundle.
4. **Wrap the app with Capacitor + ship to Google Play ($25 one-time -- the only paid step).** Scaffold Capacitor against `console/out`, resolve the `basePath:'/console'` load, generate PNG launcher/splash assets, produce a signed `.aab`, register the $25 Play Console, file a data-safety form matching the real stack (location + accelerometer, on-device). Bundle push via free ntfy UnifiedPush, not Google FCM.
5. **Finish the two half-built consumer hooks (free).** Route transit/flights/trains through `upsert_event` so "fused feeds" is true, and port the Web Speech `speak()` helper into the console so alerts are actually spoken -- the "commuter news station" is a browser-native TTS call away, no server cost.

Everything except move 4 is $0. Free-first golden rule holds.

---

## Pricing + tiers (FUTURE, not built)

**None of this exists in code.** No Stripe, no billing, no subscriptions, no accounts to bill against (`grep` for stripe/checkout/webhook/price_id is clean). This is a target model to build **after** accounts land (move 3), with the plan string on the user row and access enforced in FastAPI, not the client:

| Tier | Price | Intended audience |
| --- | --- | --- |
| Free | $0 | Basic live map + advisories |
| Pro | $4.99/mo | Full feeds + escape routing |
| Gig Pro | $9.99/mo | Gig-driver presence + multi-stop + intel |
| Guardian | $19.99/mo | Crash auto-SOS + per-user emergency contacts + push |
| Trusted Citizen | $99.99/mo | Verified/identity tier + report trust-scoring |
| Enterprise | custom | Fleet / org deployments |

Note: the in-repo `AROUNDME_PIVOT.md` actually proposes a **simpler Free + $2.99-4.99 model**, not this 6-tier structure. Reconcile before building. No tier is buildable until multi-user auth ships.

---

## Legal + ethics line

**Posture: show only unencrypted public-safety dispatch. Never surface tactical/SWAT, juvenile-victim, officer names, or federal talkgroups. Never ingest encrypted-channel content.**

This posture is **not yet enforced -- the opposite is currently live**, and that is the most important honest disclosure in this handoff:

- `radio.py` extracts "juvenile" + person descriptions + CA plates, assigns persistent codenames to officer units, and decodes tactical traffic (shots fired, foot pursuit, in custody, code 3).
- `feeds.py` even lists a "Vallejo Fire (PD priority encrypted)" feed by name with no suppression.
- The advisory disclaimer IS shipped and live ("Advisory only, not an official order. Follow 911 and local authorities." on evacuate/shelter/WAYS OUT cards) -- that part is DONE.

**Required before any public launch:**

1. **Ethics allow-list filter** in `scanner_pipeline.py`/`radio.py` that drops juvenile-victim, officer-name, SWAT/tactical, and federal content **before** SQLite persistence, and never ingests encrypted channels.
2. **Server-side legal reframe** (move 2) so risk-scores and person/plate extraction never leave the server in the public build.
3. **Privacy + consent gate:** no privacy policy, terms, consent UI, or delete-my-data endpoint exists today; `reports.py` stores a client id + lat/lon with no consent record, and the GPS beacon POSTs to `/api/location` with only a token. Add a first-run location-consent gate, static `/privacy` + `/terms` routes in the Next export, and a real `DELETE` data endpoint before any user location or report is written.
