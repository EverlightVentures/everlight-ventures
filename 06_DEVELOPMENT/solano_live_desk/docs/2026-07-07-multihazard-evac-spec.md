# Solano Live Desk -> Multi-Hazard Survival OS (spec v3 addendum)

**Date:** 2026-07-07
**Extends:** `2026-07-07-secops-upgrade-spec.md` (which extended the Phase 1 design)
**Status:** Approved vision; adds the natural-disaster / CBRN / evacuation / cascade layers

---

## 1. What it becomes (v3)

A personal multi-hazard survival OS: criminal + natural disaster + CBRN awareness, government
safe-zone data, danger-avoiding evacuation routing, and defensible cascade prediction. Personal
first, productizable second (public-safety situational-awareness market: Genasys/Zonehaven,
Watch Duty, Dataminr, Samdesk, Perimeter, RapidSOS). Everything free/public/legal.

## 2. Multi-hazard feed stack (all free, GPS-keyable, verified 2026-07-07)

| Hazard | Source | Endpoint | Auth | Notes |
|---|---|---|---|---|
| Severe wx / flood / tornado / heat / winter / RedFlag / TSUNAMI / civil-evac | NWS (in 2A) | `api.weather.gov/alerts/active?point=LAT,LON` | keyless (UA req) | Backbone; ~60% of hazards in one call |
| Earthquake | USGS FDSN | `earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude=&longitude=&maxradiuskm=&starttime=&minmagnitude=` | none | Point-keyable |
| Wildfire hotspots | NASA FIRMS | `firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{w,s,e,n}/{days}` | free MAP_KEY | bbox; corroborate w/ CAL FIRE |
| Wildfire perimeters/containment | CAL FIRE | `incidents.fire.ca.gov/umbraco/api/IncidentApi/List?inactive=false` (+ GeoJsonList) | none | CA only; undocumented |
| Smoke / AQI | AirNow | `airnowapi.org/aq/observation/latLong/current/?latitude=&longitude=&distance=&API_KEY=` | free key | Hourly |
| Tsunami geometry | NWS Tsunami | `tsunami.gov/events/xml/PAAQCAP.xml` (+ PHEBCAP) | none | US covered by NWS point too; dedupe |
| Volcano | USGS HANS | `volcanoes.usgs.gov/hans-public/api/volcano/getCapElevated` | none | Cascades/AK/HI |
| Global multi-hazard | GDACS | `gdacs.org/gdacsapi/api/events/geteventlist/MAP` + `xml/rss.xml` | none | CC BY 4.0; global safety net |
| Radiation (baseline, NOT realtime) | Safecast | `api.safecast.org/measurements.json?latitude=&longitude=&distance=` | none | Historical/crowd; label clearly |

**NOT freely available (disclose, never fake):** USGS ShakeAlert raw earthquake EARLY-warning
(licensed MOU; civilians get MyShake/WEA only), FEMA IPAWS OPEN feed (registration-gated),
real-time CBRN / nuclear-blast civilian detection (does not exist free; NUKEMAP is a simulator).
Watch Duty has no public API (ToS-protected) -> use FIRMS + CAL FIRE for wildfire instead.

## 3. Safe zones + evacuation routing (free)

- **Evac zones + live status (the key find):** CA Evacuation Aggregation Layer (Cal OES ArcGIS),
  `services.arcgis.com/BLN4oKB0N1YSgvY8/arcgis/rest/services/CA_EVACUATIONS_CalOESHosted_view/FeatureServer/0/query?where=1=1&outFields=*&f=geojson`
  Fields: `STATUS` (NORMAL / EVACUATION WARNING / EVACUATION ORDER / SHELTER IN PLACE), `ZONE_ID`,
  `ZONE_NAME`, `EVENT_TYPE`. Covers Solano/Bay Area, 5-min refresh, 2000 recs/query (paginate).
- **Open shelters:** FEMA NSS OpenShelters ArcGIS `gis.fema.gov/arcgis/rest/services/NSS/OpenShelters/MapServer/0/query?f=geojson` (disaster-gated; often empty in bluesky).
- **Fallback safe points:** OSM Overpass `around` for amenity=hospital|police|fire_station|shelter, emergency=assembly_point.
- **Routing (avoid danger polygons):** self-host **Valhalla** on e5 (ARM64), `exclude_polygons`
  = merged danger set (evac ORDER polygons + CHP/511 incident buffers + CAL FIRE perimeters),
  request `alternates`. OSM tiles from Geofabrik California. GraphHopper `custom_model` = equal
  fallback. OSRM rejected (no avoid-polygon). Bind 127.0.0.1.
- **Real-time traffic FLOW = not free (honest gap).** No free live congestion/foot-traffic. Proxy
  = incident-based avoidance (511 events + WZDx + CHP + Caltrans closures + evac ORDER polygons):
  routes around closed/blocked/on-fire/under-order roads (the 90% that matters for egress). Live
  bumper-to-bumper optimization is the paid 10% (TomTom/HERE flow key) -> revisit only at product scale.

## 4. Cascade engine (real science, do-not-claim enforced IN CODE)

Pattern: `trigger -> derived watch -> confidence label (High|Medium|Low) -> recommended action`.

**Allowed cascades:**
- Active fire -> erratic-behavior/plume watch (NWS Spot Forecast + wind + FIRMS growth). Medium.
- Fire growth acceleration (FIRMS hotspot expansion). Medium.
- Large (M7+) shallow OFFSHORE quake -> tsunami (NOAA official product only). High.
- Tsunami -> coastal arrival time (NOAA travel-time/DART). High arrival / Medium amplitude.
- Post-fire burn scar + rain -> debris flow / flash flood (USGS + NWS). Medium-High.
- Manhunt/pursuit -> reachable-area estimate: isochrone from last-known + elapsed time (foot ~3-5mph,
  vehicle road-network-bounded), constrained by barriers, decaying confidence. Label ESTIMATE;
  "official perimeter supersedes". Low/Heuristic.

**HARD-BLOCKED (suppressed in code, never asserted):** earthquake -> volcano; earthquake time/place
prediction; distant tsunami -> far-inland/non-facing coast; small/local/onshore quake -> tsunami;
"firestorm/pyroCb" as a forecast (only observed/nowcast via GOES). A derived watch may NEVER be
worded as an official warning; provenance + confidence are stored with every watch.

## 5. SDR-free audio: the honest verdict

Physics: no receiver = no RF. Only no-personal-hardware path = consume someone else's shared feed.
- **OpenMHz (free API): ZERO Solano coverage** (nearest = Sacramento SRRCS, intermittent). Free +
  no-hardware = nothing for Solano today.
- **Broadcastify Premium (~$30/yr): Solano IS covered** by a volunteer Calls node (Fairfield/Suisun/
  Vacaville/Dixon/Rio Vista PD + Sheriff + CHP + Fire; NOT Vallejo/Benicia). Premium unlocks Calls
  archive + playlist -> pull per-call audio+metadata -> whisper.cpp on e5. No hardware. Personal-use
  only (ToS bars redistribution -> matters if productized). Depends on one volunteer (no SLA).
- **Decision (free-first, ask-before-spend):** (a) $30/yr Broadcastify Premium (no hardware, works
  now), (b) free standalone SDR node he never carries (Pi + RTL-SDR at a fixed spot), or (c) wait for
  an OpenMHz volunteer. Recommend (a) for immediacy; (b) is the free-forever path if a fixed spot exists.

## 6. SaaS framing (personal-first, productizable)

Market = public-safety situational awareness / mass-notification / evacuation. Architectural
implications baked in now so it can scale later: (1) multi-tenancy from day one (isolate tenant
data even while single-user); (2) per-tenant geofencing / configurable AOIs (not hardcoded Solano);
(3) data-source licensing changes at commercial scale (Broadcastify/OpenMHz personal-only; commercial
needs licensed feeds or owned SDR + NWS/USGS/NASA terms review); (4) confidence + provenance as a
first-class feature (gov buyers need auditable "why did it warn"; also the pseudo-science liability shield).

## 7. Updated roadmap

- 1 DONE: live incident map. 2A DONE: follow-me + threat engine + NWS.
- **2B (building now):** alerts (ntfy push + email by threat) + DVR (master incident store + retention).
- 2C: multi-hazard feeds (USGS/FIRMS/CALFIRE/GDACS/AirNow) folded into the same threat engine + map;
  Caltrans camera auto-pull + YOLO congestion; Broadcastify live-listen tray.
- 2D: safe-zones (CA Evac Aggregation Layer + shelters) on the map + threat overlay.
- 3: PSIM dashboard (AMAG-style alarm queue, alarm-to-video, case reports).
- 3B: evacuation routing (self-host Valhalla, avoid danger polygons, alternates).
- 3C: cascade engine (allowed cascades + do-not-claim guardrails + provenance).
- 4: audio -> whisper (Broadcastify Premium OR standalone SDR node; pending decision).
- 5: phone-as-dashcam roving eye.
- 6 (optional): multi-tenant SaaS hardening.
