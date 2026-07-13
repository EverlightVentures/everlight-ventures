# AroundMe: Complete Handoff for a New Assistant

Written 2026-07-12. This is the single self-contained brief. If you are a new
assistant picking this up cold, read this top to bottom and you can be productive
immediately. For deeper detail, the four canonical docs are in `docs/`:
`AGENT_HANDOFF.md` (this file), `project_handoff.md` (honest feature audit),
`AROUNDME_PIVOT.md` (the roadmap + design rationale), `AROUNDME_BRAND_GTM.md`
(brand, go-to-market, IP).

---

## 1. What AroundMe is

AroundMe (repo codename "Solano Live Desk") is a real-time personal-safety and
situational-awareness map. It fuses about 18 free public data feeds into ONE live
map centered on the user's GPS, scores every incident by threat and proximity,
tells the user whether to shelter or evacuate and which way to go, and pushes
life-safety alerts to their phone.

It started as a private tool for one gig-delivery driver in Solano County,
California, and is being repositioned into a mass-market app ("AroundMe") for gig
drivers, truckers, digital nomads, and survivalists. Owner: Rich Gee, under
Everlight Ventures. It is aligned with Everlight Logistics.

Root principle (Everlight): solve multiple logistics problems with the least
resources, free-first, minimalist, morally grounded, aggressive but protective.

Today it is a WORKING single-operator product. It is NOT yet the multi-user
consumer app the long roadmap describes (no accounts, no billing, no native app).

---

## 2. The real stack (do NOT assume otherwise)

Various planning docs floated a Firebase + Mapbox + React Native stack. We use
NONE of that. The real stack is:

| Concern | What we actually use |
| --- | --- |
| Backend | Python FastAPI (`sld/` package), served by uvicorn |
| Data store | Per-day SQLite: `store/events_YYYY_MM_DD.db` (NOT a cloud DB). Separate `store/reports.db` for user reports. Single global store, no user dimension yet. |
| Frontend | Next.js 14 App Router, static export (`output: "export"`), served by FastAPI at `/console` |
| Map | MapLibre GL + react-map-gl (NOT Mapbox/Google) |
| Routing | Free OSRM (`router.project-osrm.org`) + OpenStreetMap Overpass/Nominatim (NOT Mapbox Directions) |
| Push | ntfy.sh (free), one topic |
| Host | Free Oracle ARM VM called "e5", one `solano-desk.service` |
| Auth | Single `SLD_ACCESS_TOKEN` magic-link cookie gate. No user accounts. |

Free-first is a hard rule. Exhaust free/self-host before any paid option, and ask
before spending.

---

## 3. Repo map

Path: `06_DEVELOPMENT/solano_live_desk/` inside the `AA_MY_DRIVE` git repo.
Branch: `solano-live-desk`.

```
sld/                     FastAPI backend (~43 modules)
  api.py                 all HTTP + WebSocket endpoints
  store.py               per-day SQLite: connect/upsert/get_events/today_pt/on_day
  ingest.py              the feed-poll loop (writes the day DB)
  broadcaster.py         WebSocket change-detector (pushes deltas to /ws)
  threat.py              severity x proximity-ring scoring -> threat_level
  correlate.py           union-find fusion, confidence tiers, incident lifecycle
  decide.py              shelter-vs-evacuate decision engine (+ bearing to hazard)
  escape.py              Dispersed Egress smart multi-route escape routing
  reports.py             community reports + gig-driver "on delivery" presence
  routing.py             OSRM wrapper + danger_features (things to avoid)
  roads.py, wayfinding.py, geo.py, geo_county.py   geo helpers
  notify.py, alerts.py, alert_worker.py            alert routing + ntfy/email push
  Feed modules: chp_parser, nws, firms, quakes, fema, aircraft, trains, transit,
    evac, webcams, cameras, camera_dvr, dvr, broadcastify, scanner_pipeline,
    transcribe, radio, meshtastic_mesh, social, news, spacewx, feeds, hub, config
console/                 Next.js frontend (package.json lives on e5 at ~/psim, NOT here)
  app/page.tsx           the whole single-page app (map + panels + effects)
  app/layout.tsx         metadata (AroundMe title, iOS install meta, fonts)
  components/            MapView, DetailDrawer, AlarmQueue, CrashGuard, ReportPanel,
                         Toolbar, Scrubber, FilterBar, Legend, StatusBar, StatsPanel,
                         NewsPanel, LiveVideo, SourceBadge, KillSW, MiniMap
  lib/api.ts             all fetch helpers
  lib/mode.ts            PUBLIC_BUILD flag (NEXT_PUBLIC_AROUNDME_MODE)
  lib/types.ts, lib/util.ts
  next.config.mjs        output:export, basePath:/console, assetPrefix:/console
tests/                   ~24 pytest files, 97 passing
scripts/                 deploy_console.sh, gps_beacon.sh, run/scanner/mesh runners
docs/                    the 4 canonical docs + design specs
requirements.txt         python deps (pinned)
```

---

## 4. The data pipeline

```
~18 free feeds  ->  ingest.py (poll loop, own process)  ->  per-day SQLite
     store  ->  threat.classify(event, user_gps)  [severity x proximity ring]
            ->  correlate.correlate(events)        [fuse dupes, confidence tier]
            ->  correlate.lifecycle(event)         [ACTIVE..CLEARED/CLOSED]
            ->  decide.decide(incidents, evac_zones, user)  [SHELTER/EVACUATE/CLEAR]
            ->  broadcaster (WebSocket /ws)  +  alert_worker (ntfy push)
     frontend polls /api/events + /api/correlated every 20s AND listens on /ws
```

Key model facts:
- Events are dicts: id, source, type, lat, lon, geo_label, first_seen, last_seen,
  body, severity, plus threat_level/distance_mi/ring added by `threat.classify`.
- `geo_county.distance_mi(a, b)` takes TWO (lat,lon) TUPLES, not 4 floats.
- Daily reset: the live view filters to `store.on_day(last_seen, today)` so
  yesterday's stragglers drop off. Archived days are viewable via the `date` param.

---

## 5. The feeds (all free/public)

CHP traffic incidents (CA), 511 Bay Area traffic + transit (GTFS-RT, needs
`SLD_511_TOKEN`), NWS weather alerts, USGS earthquakes, NASA FIRMS wildfire
hotspots, Cal OES evacuation zones (ArcGIS), Broadcastify scanner audio + Whisper
transcription, ADS-B flights (adsbdb), Amtrak/rail, Meshtastic mesh (MQTT),
Reddit/Mastodon/Bluesky safety chatter, FEMA, DOT/public webcams, NOAA space
weather. CHP/511/CalOES are California-only; NWS/USGS/FIRMS are national.

---

## 6. API endpoints (FastAPI, all under the site root, not /console)

Read: `/api/events`, `/api/correlated`, `/api/incidents`, `/api/days`,
`/api/stats`, `/api/county`, `/api/feeds`, `/api/where`, `/api/evac`,
`/api/safepoints`, `/api/danger`, `/api/route`, `/api/decision`, `/api/escape`,
`/api/reports`, `/api/aircraft`, `/api/trains`, `/api/transit`, `/api/flight`,
`/api/cameras`, `/api/webcams`, `/api/cam_dvr`, `/api/camframe/...`,
`/api/scanner_near`, `/api/event_transcript`, `/api/scanner_audio/...`,
`/api/intel`, `/api/links`, `/api/social`, `/api/social_hotspots`, `/api/mesh`,
`/api/spacewx`, `/healthz`.

Write: `POST /api/location` (GPS beacon, token query-param allowed through the
gate), `POST /api/sos` (crash/manual SOS -> priority-5 ntfy), `POST /api/report`
(reckless/hazard), `POST /api/presence` (gig "on delivery"). WebSocket: `/ws`
(live snapshot + deltas). `GET /unlock/{token}` sets the private-gate cookie.

---

## 7. Frontend behavior (console/app/page.tsx)

Single fixed-position map app. On load it: watches GPS (`watchPosition`, posts to
`/api/location`), centers + follows the user (YOU marker), polls events/fused every
20s, connects `/ws` for live deltas, and fetches the shelter/evacuate decision.
Overlays: AlarmQueue (ranked incident list), DetailDrawer (tabs: Feed, Transcript,
Mesh, Intel, Social, Audio, Cameras, Sources), decision card (tap an EVACUATE card
to draw escape routes via `/api/escape`), CrashGuard (accelerometer SOS +
bottom-right SOS/Guard buttons), ReportPanel (bottom-center Report/voice/delivery
controls), Toolbar (layer toggles), Scrubber (time replay), FilterBar, Legend.

---

## 8. Feature status (from the audit: 14 DONE, 22 PARTIAL, 25 PLANNED)

DONE and live: the ~18-feed fusion, threat matrix, correlation + lifecycle, the
shelter/evacuate decision engine, Dispersed Egress smart-escape routing
(`/api/escape`), crash detection + SOS (`/api/sos`, foreground-web only),
reckless-driver + hazard reports with dedup + severity escalation (`/api/report`),
gig-driver "on delivery" self-marking (`/api/presence`), voice reporting (Web
Speech API), daily-reset, the AroundMe rename + iOS add-to-home install meta, the
legal-reframe build flag (frontend), the background GPS beacon, ntfy push.

PARTIAL: NWS shows as point markers only (polygon thrown away), scanner + mesh run
but their deps were unpinned (now fixed), the "legal reframe" hides risk-score +
entities in the frontend only (backend still serves them), SOS pushes to one
shared topic, crash detection is foreground-only.

PLANNED (not built): Capacitor native app + Google Play, accounts + multi-user
backend, Stripe billing + the 6 pricing tiers, audio "commuter news station" TTS +
ducking, siren detection ML, weather route-polygon intersection + storm tracking,
turn-by-turn navigation, crowdsourced human confirmation, RTL-SDR nodes.

Full per-feature table with evidence + next steps: `docs/project_handoff.md`.

---

## 9. How to run, test, build, deploy

Work happens on Rich's phone (Termux + proot Debian). The phone is DEV. e5 is
PROD. The phone CANNOT `npm install` (SIGSEGV) so the frontend is always BUILT ON
e5.

Test (from the project dir on the phone):
```
python3 -m pytest -q
```

Deploy backend (Python):
```
rsync -az sld/<changed>.py e5:~/solano_live_desk/sld/
ssh e5 'systemctl --user restart solano-desk.service'
```

Deploy frontend (console). ALWAYS clean-build first (its cache ships stale
components). Gate the build before publishing:
```
rsync -az --exclude node_modules --exclude .next --exclude out console/ e5:~/psim/
ssh e5 'cd ~/psim && rm -rf .next out && npm run build'      # gate: must compile clean
ssh e5 'rm -rf ~/solano_live_desk/web/console && cp -r ~/psim/out ~/solano_live_desk/web/console && systemctl --user restart solano-desk.service'
```
There is a wrapper: `scripts/deploy_console.sh` (does all three steps).

Public-app build (hides legal-risk features): prefix the build with
`NEXT_PUBLIC_AROUNDME_MODE=public`.

---

## 10. Infrastructure and access

- e5: Oracle ARM VM. Reach with `ssh e5` (primary, 163.192.60.35) or
  `ssh e5-public` (break-glass). Never `pkill` a running command on it.
- Services (systemd --user): `solano-desk.service` (the app, binds 127.0.0.1:2600),
  `solano-mesh` (Meshtastic collector), `solano-tunnel` (cloudflared),
  `solano-watchdog`.
- Live URLs: `https://survival.everlightventures.io/console/` (public, behind the
  private magic-link gate) and tailnet `http://100.125.115.95:2600`. `/healthz`
  and `/unlock/{token}` bypass the gate.
- Store: `~/solano_live_desk/store/` (per-day event DBs + `reports.db` +
  `last_location.json`). Published console: `~/solano_live_desk/web/console/`.
  Next build project: `~/psim/` (this holds `package.json` + `node_modules`).
- Env (e5 `.env`): `SLD_ACCESS_TOKEN` (gate), `SLD_NTFY_URL`
  (`https://ntfy.sh/ev-survival-3433cb786562ba2e`), `SLD_STORE` (default "store"),
  `SLD_511_TOKEN`, `SLD_PUBLIC_HOST`.
- Push: subscribe the ntfy Android app to topic `ev-survival-3433cb786562ba2e` to
  receive SOS/alerts. (Right now every user shares this one topic; per-user topics
  are a needed next step.)
- GPS beacon: `scripts/gps_beacon.sh` runs Android-side in Termux (Termux:API +
  Termux:Boot), posts location every 60s so alerts fire with the app closed.

---

## 11. Critical gotchas (the landmines)

1. Phone (proot) cannot `npm install` -> build the console on e5, always.
2. No em-dash character anywhere. A PreToolUse hook blocks any file write that
   contains one. Use plain hyphens.
3. `deploy_console.sh` MUST `rm -rf .next out` before build or it ships stale UI.
4. `next.config.mjs` sets `basePath: "/console"`. A Capacitor native build loads
   from the app bundle root, so `/console` absolute paths break; the native build
   needs `basePath: ""` (or point `capacitor.config.server.url` at the e5 host).
5. `KillSW.tsx` unregisters every service worker + purges caches on load (it exists
   to defeat stale `/console/` caching). This also blocks offline/installable PWA
   behavior; revisit before packaging.
6. `lib/mode.ts` `PUBLIC_BUILD` only gates the REACT tree. The FastAPI
   `/api/intel` and `/api/links` still COMPUTE and SERVE the risk-score + plate/
   person entities as open JSON, and `radio.py` still extracts them. Before any
   public launch, gate these on the BACKEND too.
7. `distance_mi` takes two (lat,lon) tuples, not four floats.
8. Do NOT rebuild features on a Firebase/Mapbox assumption. Map every idea onto
   the real stack in section 2.

---

## 12. Must-fix before AroundMe goes public

1. Backend-gate the legal-risk endpoints (`/api/intel`, `/api/links`, radio
   entity extraction) so the reputation-score + person/plate data is not served at
   all in public mode. This is a Fair-Housing / defamation exposure (the Citizen
   backlash pattern). See `AROUNDME_PIVOT.md` legal reframe.
2. Per-user SOS contact: today SOS goes to one shared ntfy topic. Store a per-user
   topic (localStorage -> passed to `/api/sos`) so "emergency contact" is real.
3. File the USPTO intent-to-use trademark for "AroundMe" (Class 9 + 42) under
   Everlight before public launch, and grab the domains/handles. See
   `AROUNDME_BRAND_GTM.md`. This costs money (~$250-350/class); Rich's call.

---

## 13. The real next moves (free unless noted)

1. Backend-gate the risk endpoints (above).
2. Per-user SOS topic (above).
3. Insurance driving-score primitive: extend CrashGuard to count sub-crash
   hard-brake/accel events + miles from the beacon into a weekly 0-100 score card.
   This is the B2B revenue hook (usage-based insurance). Consent gate is mandatory.
4. Siren detection on the phone mic (YAMNet / TF.js, free, no dongle) to fill the
   scanner gap the operator most cares about.
5. Capacitor Android build for Google Play. Focus Android, skip Apple for now.
   Only paid step is the $25 Google Play Developer account. Watch gotcha #4 + #5.

---

## 14. Brand / GTM / IP (see docs/AROUNDME_BRAND_GTM.md)

Name: AroundMe, Everlight-aligned. Play Store line (locked):
"The GPS for gig drivers, digital nomads and survivalists." Hero tagline:
"know what's around you, before it reaches you." The unique hooks nobody else has:
the reckless-driver warning, the gig-driver "delivery, not a prowler" self-marking,
and scanner-fed pre-arrival awareness. Grab `aroundme.app`, `@aroundmeapp`, Play id
`com.everlight.aroundme`. File the trademark BEFORE going public (press day is
copycat day).

---

## 15. Conventions

- Commit only when the owner asks. Branch first (never commit straight to `main`).
  Push side-branch first. Git over SSH (key `github_deploy`; HTTPS TLS is broken in
  proot). End commit messages with the Co-Authored-By trailer.
- Everlight brand palette (if you build human-facing docs): gold `#D4AF37`, dark
  `#0A0A0A`, light text `#E8E8E8`, Playfair Display + Inter.
- Operator-truth doctrine: failures lead the report, DONE means a verified receipt,
  PLANNED means "next". Never claim something works without verifying it live.
- Prove-real: after deploying, curl the live endpoint / check the published file and
  show the result. Do not assert; verify.
```
