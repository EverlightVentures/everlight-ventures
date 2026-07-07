# Solano Live Desk -- Design Spec

**Date:** 2026-07-07
**Owner:** Rich Gee (operator) / Lucrex (build)
**Status:** Approved design, pre-implementation
**Project root:** `06_DEVELOPMENT/solano_live_desk/`

---

## 1. Vision

A personal, real-time news feed for Solano County, CA rendered as a live map. It shows
what is actually happening right now: CHP incidents, fire/EMS calls, and traffic-camera
visuals, with the dispatch reports in text, live scanner audio you can listen to, a
scrub-back timeline, and a "PI corkboard" yarn layer where AI links events that share a
place, time, or entity. It resets each day at local midnight (PT) but archives every past
day so you can rewind to any moment and see the traffic and read/hear the reports.

Not a public product. A private instrument for one operator who lives mobile (car + phone).

## 2. Non-negotiable guardrails (baked in from commit 1)

- **Public-safety information only.** Incidents, traffic, fire/EMS dispatch. No surveillance
  of private individuals, no facial recognition, no license-plate reading, no person-tracking.
- **Honor every source's Terms of Service.**
  - CHP `sa.xml` and Caltrans CCTV JSON are public, no-auth government feeds, free to poll.
  - **Broadcastify audio is EMBED-ONLY.** We render Broadcastify's official player for live
    human listening (allowed). We do NOT scrape, restream, capture, or server-side
    transcribe their audio (prohibited by their ToS). This is a hard line.
- **Archive, never delete.** Daily partitions roll over but old days are archived
  (matches the workspace no-deletion doctrine + memory pipeline).
- **Free-first.** Every component is free/open-source or a free public feed. No paid tier.
- **Private by default binding.** Service binds `127.0.0.1` on e5-mother, exposed to the
  phone via tailnet, or via Cloudflare on an `*.everlightventures.io` host if off-tailnet
  access is wanted (per Network Binding Doctrine, use `EV_BIND`).

## 3. Verified data sources (confirmed live 2026-07-07)

### 3.1 CHP incidents -- PRIMARY backbone (CONFIRMED)
- **Endpoint:** `http://media.chp.ca.gov/sa_xml/sa.xml` GET, no params, no auth, XML.
  Statewide, filter client-side.
- **Filter chain for Solano:** `Center ID="GGHB"` -> `Dispatch ID="GGCC"` (Golden Gate
  Comm Center #318, Vallejo, dispatches all 9 Bay Area counties) -> keep logs where
  `Area == "Solano"`. Fallback: text-match city names (Fairfield, Vacaville, Vallejo,
  Benicia, Suisun, Dixon, Rio Vista) + route numbers (I-80/I-680/I-505/SR-12/SR-37/SR-113).
- **Per-incident schema:** `LogTime`, `LogType`, `Location`, `LocationDesc`, `Area`,
  `ThomasBrothers`, `LATLON`, and `<LogDetails>` -> repeating `<details>`
  (`DetailTime` + `IncidentDetail`) + `<units>` (`UnitTime` + `UnitDetail`). The
  `LogDetails` lines are the running dispatch narrative = the "written transcript."
- **Coordinates:** `LATLON` = `"lat:lon"` as micro-degree integers. Decode: `lat/1e6`,
  `lon/1e6` (longitude is West, negate). `"0:0"` = unknown, geocode `Location` text or
  drop to Solano centroid.
- **Poll cadence:** every 60s. De-dup on `(Dispatch ID, Log ID)`, append new `details`
  lines to the existing event so the ticker grows.
- **Reference parser to fork:** `github.com/lectroidmarc/SacTraffic` (ISC, archived, own
  the fork). Poll cadence reference: `github.com/carbonphyber/watch-california-highway-patrol-incidents` (MIT).

### 3.2 Caltrans District 4 cameras -- visuals (CONFIRMED)
- **Endpoint:** `https://cwwp2.dot.ca.gov/data/d4/cctv/cctvStatusD04.json` GET, no auth, JSON.
- **Filter:** `location.county == "Solano"` (and route-match SR-37/SR-12 if county field
  is sparse). NOTE: enumerate the RAW json, it holds hundreds of cameras across 9 counties,
  do not trust a truncated sample.
- **Per-camera fields:** `index`, `recordTimestamp`, `location{locationName, nearbyPlace,
  latitude, longitude, county, route, postmile, direction}`, `inService`,
  `imageData{currentImageURL, streamingVideoURL, ...historical}`.
- **Read `currentImageURL` (JPEG snapshot) and `streamingVideoURL` (HLS m3u8) directly**,
  no URL construction. Refresh snapshot every ~60-120s.
- Confirmed live example: TV976 I-80 @ Suisun Valley Rd, Fairfield (38.22374, -122.12696).

### 3.3 Scanner audio -- LIVE-LISTEN EMBED ONLY (Broadcastify)
- Solano feeds (free to listen in browser, embed the official player, do NOT scrape):
  - **4881** Fairfield/Vacaville/Suisun Police, Fire & EMS
  - **28814** CHP Solano (I-80/I-680)
  - **20773** Solano Sheriff, Rio Vista & Dixon PD
  - **45149 / 44166** multi-agency PD+Fire+CHP
  - **32738 / 45148 / 43524 / 41964 / 1883 / 46513** Solano Fire
  - **45005** Solano CAL FIRE, **39356** Benicia Fire, **820** Vallejo (fire + non-priority)
- Each feed is pinned to its coverage zone, clicking a zone opens the relevant player.
- **Encryption reality (set expectations in UI):** clear today = Fairfield PD, Vacaville PD,
  Suisun PD, Dixon PD, Rio Vista PD, Solano Sheriff, county Fire/EMS, CAL FIRE, CHP dispatch.
  Unavailable (encrypted) = Vallejo PD (since 2021), Benicia PD (encrypting ~2026), all
  tactical/SWAT/investigations. The live feeds are the canary: if one goes silent, an
  agency likely encrypted.

### 3.4 Public webcams -- ambient (curated list)
- A small curated JSON of public webcam stream/snapshot URLs around Solano, pinned as
  ambient context. Hand-maintained, additive, non-critical.

### 3.5 Transcription -- DESIGNED-IN, DORMANT
- There is NO free, legal, auto-transcribable Solano scanner feed today (OpenMHz has
  no Solano system, Broadcastify is embed-only). The CHP `LogDetails` text is the working
  substitute for "reports in writing."
- The transcription interface is built but disabled. It activates only when a permitted
  audio source exists: (a) an OpenMHz Solano system appears
  (`GET https://api.openmhz.com/{shortName}/calls` -> `.m4a` URLs, browser-like UA required),
  or (b) the operator opts into his own SDR later.
- Engine when activated: **whisper.cpp** (MIT) via **pywhispercpp** (MIT), one-shot per clip,
  model `base.en` (near-realtime on ARM CPU), `tiny.en` for speed, `small.en` for offline
  re-processing. Fallback engine: **faster-whisper** (MIT, int8/CTranslate2).

## 4. Architecture

```
                         e5-mother (always-on, ARM64, tailnet)
  +-----------------------------------------------------------------------+
  |  ingest daemons (asyncio loop, 60s tick)                              |
  |    - chp_ingester   -> parse sa.xml, filter Solano, upsert events     |
  |    - cam_ingester   -> refresh Caltrans D4 Solano cameras + snapshots |
  |    - webcam_ingester-> refresh curated webcam list                    |
  |  enrich                                                                |
  |    - geocoder       -> decode LATLON / reverse-geocode (Nominatim     |
  |    |                    public, 1 req/s, cached) / centroid fallback  |
  |    - entity_extract -> streets, routes, vehicle desc, incident type,  |
  |    |                    agency (regex + Solano gazetteer, Haiku later)|
  |    - linker         -> edges on shared geo(radius)/time(window)/      |
  |                        entity, weight = # dims matched                |
  |  digest (hourly)    -> cluster day's events, summarize + flag pattern |
  |                        (Claude Haiku, cheap, batched)                 |
  |  store: SQLite, ONE FILE PER DAY  events_YYYY_MM_DD.db (append-only)  |
  |  api: FastAPI  /events /links /cameras /feeds /digest /day/<date>     |
  |  web: one static page (MapLibre + time-slider + yarn + player embeds) |
  +-----------------------------------------------------------------------+
                        |  tailnet  or  Cloudflare (ev domain)
                        v
                   Phone browser = viewer (+ optional GPS re-center)
```

- **Runs on e5-mother only.** Phone is a window (proot cannot run Whisper/heavy node, not
  always-on). Deploy via the e5 provisioning kit pattern.
- **Phone viewer:** opens one URL. Default map view = Solano County. "Follow-me" toggle
  re-centers on live GPS + adds a radius (mobile-native, operator is in a car).

## 5. Data model

**Event** (one row per incident/camera-event):
```
id                TEXT  PK   (source-prefixed: "chp:GGCC:<logid>")
source            TEXT       chp | camera | webcam | (audio, later)
type              TEXT       incident type / "camera" / etc.
title             TEXT
lat, lon          REAL       nullable (0:0 -> null -> geocode/centroid)
geo_label         TEXT       human location string
first_seen        TEXT (ISO, PT)
last_seen         TEXT (ISO, PT)
body              TEXT       running dispatch log lines (CHP) joined
entities          JSON       {streets:[], routes:[], vehicles:[], agency:[], type:""}
raw               JSON       original payload for audit
```
**Link** (yarn edge): `id, a_event, b_event, dims JSON (["geo","time","entity"]), weight INT`.
**Camera**: `id, name, lat, lon, route, county, image_url, stream_url, updated`.
**Feed** (scanner): `id, name, agencies[], zone_geojson, broadcastify_id, status`.
**Digest**: `id, day, generated_at, summary, clusters JSON, patterns JSON`.

Store = SQLite, **one DB file per day** (`store/events_2026_07_07.db`). Midnight PT -> new
file (the "reset"). Old files archived under `store/archive/`, never deleted. A `days.json`
index lists available days for the timeline's day-picker.

## 6. The yarn correlation engine

1. Every event carries `{time, geo, entities}`.
2. `linker` compares each new event to recent events and creates a Link when they share:
   - **geo**: within radius R (default 1.5 km), same scene / same corridor.
   - **time**: within window T (default 20 min), concurrent activity.
   - **entity**: shared street/route/vehicle-desc/agency/type.
3. `weight` = number of dimensions matched (1-3). Frontend draws thicker yarn for higher
   weight. Click a node -> highlight its subgraph (connected events) + show bodies/snapshots.
4. Tunable thresholds live in `config.yaml` (R, T, entity match rules).

## 7. AI daily digest (the "news outlet")

- Hourly job: pull the day's events, cluster by geo+time, ask Claude Haiku for a tight
  brief: "what's happening," notable clusters, patterns (e.g., "3 I-80 EB incidents in
  20 min -> likely chain-reaction"), similarities/differences vs earlier in the day.
- Rendered in a side panel + written to the `Digest` table. Cheap, batched, free-tier-friendly.
- This is the deliverable that turns raw pins into your news.

## 8. Frontend (one static page)

- **Base:** MapLibre GL JS (BSD-3), OSM raster or free vector tiles, centered on Solano.
- **Markers:** custom SVG pins by source/type, popups with body text, timestamps, and
  (cameras) the live snapshot + an HLS `<video>` for the stream.
- **Yarn:** Turf.js great-circle LineStrings -> native MapLibre `line` layer (simple path),
  upgrade to deck.gl `ArcLayer` via `MapboxOverlay` if animated arcs are wanted.
- **Timeline:** `opengeos/maplibre-gl-time-slider` (MIT), bottom scrubber with playback,
  its `onChange(date)` filters markers/yarn to that moment. A day-picker selects archived days.
- **Scanner:** per-zone "Listen live" buttons that open the Broadcastify official player
  (embed/iframe/new-tab per what their embed allows), clearly labeled with encryption status.
- **Digest panel:** collapsible, shows the hourly AI brief.
- **Follow-me:** geolocation toggle to re-center on the operator's position + radius ring.

## 9. Reuse manifest (all permissive unless noted)

| Piece | Repo | License | Use |
|---|---|---|---|
| CHP parse | lectroidmarc/SacTraffic | ISC (archived) | fork the sa.xml parser |
| CHP poll cadence | carbonphyber/watch-...-incidents | MIT | cron/de-dup pattern |
| Transcribe (later) | ggml-org/whisper.cpp + absadiki/pywhispercpp | MIT | dormant engine |
| Transcribe alt | SYSTRAN/faster-whisper | MIT | fallback |
| Map | maplibre/maplibre-gl-js | BSD-3 | base map + markers |
| Timeline | opengeos/maplibre-gl-time-slider | MIT | scrubber |
| Yarn | Turfjs/turf (+ visgl/deck.gl) | MIT | edge lines / arcs |
| Geocode | Nominatim public (komoot/photon if self-host) | policy / Apache-2.0 | reverse-geocode labels |

Avoid vendoring: trunk-recorder (GPL), self-host Nominatim (GPL), openmhz/trunk-server
(license unclear), reference/consume-API only.

## 10. Build order (revised post-verification)

- **Phase 1 -- Live incident map (this week):** CHP ingester -> SQLite day-store -> FastAPI
  `/events` -> MapLibre page with GPS pins + popups showing the dispatch log text +
  time-slider scrub + daily reset/archive. A real, working live feed.
- **Phase 2 -- Eyes + ears:** Caltrans Solano cameras (pins + snapshots + HLS) and
  Broadcastify per-zone live-listen embeds. Public webcams.
- **Phase 3 -- The yarn + the news:** linker (geo/time/entity edges) + hourly AI digest.
- **Phase 4 -- Dormant transcription hook:** wire the whisper.cpp interface behind a flag,
  activated only if a permitted Solano audio source appears.

**Rejected alternatives:** all-on-phone (proot cannot run the engine, not always-on),
Django/Supabase-first (Django deferred, overkill, SQLite ships faster, sync summaries to
Supabase later), OpenMHz auto-transcription (no Solano coverage), Broadcastify
scrape+transcribe (ToS violation).

## 11. Open risks

- **Encryption creep** -- Solano PD dispatch is clear today but the county P25 system is
  expanding, dispatch could encrypt with no notice. Live feeds are the canary.
- **CHP `Area="Solano"` exact string** -- verify against one live GGCC record, keep the
  city/route text-match fallback.
- **CHP `0:0` coordinates** -- many logs lack geocode, reverse-geocode text or centroid.
- **Volunteer feed fragility** -- any Broadcastify feed can drop if its operator's PC dies.
- **CHP host is old HTTP IIS** -- set timeouts/retries, it can be flaky.
