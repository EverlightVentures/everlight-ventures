# Survival Console - Closed-Loop Upgrade Plan

**Goal:** Move the console from *observational* (dots on a map) to *operational* (sense, comprehend, decide, act, assess), using ONLY free/public data.

**Method:** Industry-grounded. Researched 6 reference systems (RTCC/PSIM/ICS lifecycle, Palantir Foundry/Gotham fusion, ATAK common operating picture, WebEOC/Noggin EOC, PulsePoint/Nixle/Genasys alerting, RTCC predictive/anomaly). Each capability mapped to an achievable-now feature on the data we already ingest.

**Ranking metric:** operator-safety-value / effort, with a dependency override (a foundation unlocking 3+ features is pulled forward).

---

## Already shipped this session (the "ULTRA" layer the critique asked for)
Predictive per-area risk score, transcript entity extraction (vehicle/weapon/plate), confidence tiers (UNCONFIRMED/PROBABLE/CONFIRMED), correlation + link-analysis with map lines, source-reliability badges, proximity rings, temporal decay, per-city social-hotspot anomaly baseline, 3-source social recon (Reddit+Mastodon+Bluesky), flight enrichment, bidirectional map/drawer.

---

## PHASE 1 - Build now (high value, S/M effort)

| # | Feature | Effort | Status | What real systems do |
|---|---------|--------|--------|----------------------|
| 1 | **Incident lifecycle state machine** (ACTIVE/ONGOING/WINDING DOWN/CLEARED/CLOSED) | M | **DONE** | RTCC/PSIM/ICS: every alarm is an owned case that marches to a terminal state |
| 2 | **Auto-closure engine** - CHP feed-drop diff + per-source staleness TTLs | M | next | PSIM: when the trigger clears, the alarm must close; stuck alarms auto-reap |
| 3 | **Operator ack/ownership triage** (NEW, TRACKING, MUTED) | S | planned | RTCC: every alarm has an owner; no orphan alarms; kills alert fatigue |
| 4 | **Shelter-in-place vs Evacuate decision engine** | M | building | ATAK: the map answers "stay or go," not "here are dots" - highest life-safety value |
| 5 | **Persisted narrative arc to DVR case log** | M | planned | ICS running narrative; closed case stays reviewable |
| 6 | **NWS/evac authoritative hard-close** (CAP Cancel/expires) | S | planned | Bind government machine-readable status straight to the state machine |
| 7 | **Persistent entity registry + dossier** (`entities.py`) | M | planned | Gotham dynamic ontology: raw datum to canonical object with provenance |
| 8 | **Threat-density-weighted egress** (safest route, not nearest) | M | planned | ATAK routes to the safest exit weighted by live threat density |
| 9 | Provenance/confidence audit panel | S | planned | Every fused score auditable back to its raw signals + fusion rule |
| 10 | Spatiotemporal "History here" (`/api/nearby-history`) | S | planned | RTCC: "every incident within Xmi over N days at this spot" |

### The two lifecycle closers (item 2 detail - the literal cure for "stories die")
- **Feed-drop diff:** CHP incidents vanish from `sa.xml` the instant they resolve. Diff each cycle's IDs vs. the prior cycle; any dropped open CHP event becomes `CLOSED`, reason "cleared - dropped from CHP feed." (Free closure signal, currently unused.)
- **Per-source TTLs:** CHP ~90min, scanner ~15min, NWS = its own `expires`, quake/FIRMS one-shot, auto-advance past-TTL to CLOSED with a written reason.

### Decision engine (item 4 detail - the "feel safe" core)
`sld/decide.py` fuses already-wired inputs: evac-zone status (evac.py) + nearest classified incidents/ring/type (threat.py) + NWS wind bearing (nws.py) + FIRMS hotspots (firms.py). Rules:
- Airborne hazard (gas/hazmat/fire smoke) in NEAR ring AND downwind = **SHELTER**
- Wildfire hotspot or evac Order within ~3mi, or operator inside an Order polygon = **EVACUATE** (+ route-out link)
- Active-shooter/pursuit/barricade in IMMEDIATE ring = **SHELTER / LOCK DOWN**
- else = **CLEAR** (all quiet)
Returns `{action, reason, hazard, confidence}` rendered as a persistent color-banded card (red GO / blue STAY / green CLEAR).

---

## PHASE 2 - Bigger (M/L)
- **Node-link relationship graph view** (Gotham Object Explorer) - self-contained inline force-directed SVG (CSP-safe, no CDN). Nodes = fused incidents + resolved entities; edges = correlate members + shared-entity links. *Depends on #7.*
- **Recurring-crew / co-occurrence auto-grouping** - union-find over the entity registry; entities co-appearing in 2+ incidents = "possible crew, N incidents / M days." *Depends on #7.*
- **Directional escape-corridor wedges** - upgrade proximity rings to 8 threat-weighted sectors (hot = blocked, dark = clear corridor). "Which way is open" at a glance.
- **Self status beacon / breadcrumbs** over Meshtastic (ATAK "am I OK" that survives with no cell service).

---

## PHASE 3 - Aspirational (needs data we lack - blocker named, honestly)
- **Blue-force tracking of OTHER units / shared COP** - needs a CoT server + peer devices. Solo app, no team.
- **Real unit AVL / CAD positions** - CAD/AVL/dispatch feeds are gov-gated, out of scope. Scanner transcripts are the only (delayed, partial) free proxy.
- **Confirmed identity resolution** (plate/person to real name) - no DMV/LEO DB; also a legal/privacy line. Registry stays at *observed tokens* only.
- **Hard polygon-avoidance routing** - free public OSRM cannot hard-exclude polygons; #8 exposure-scoring is the honest free approximation.
- **Predictive crew movement** - free transcripts too sparse/noisy for trustworthy forward prediction.

---

## What the critique asked for that is NOT free-buildable (and why)
Digital twin (3D building occupancy/HVAC), ALPR/plate-to-identity, ShotSpotter, bodycam/drone edge inference, neuromorphic hardware, mass-notification with read receipts, true multi-agency federated learning. All require paid platforms, hardware, or gov/enterprise data access. The plan builds the *free-data approximation* of each capability instead of cosplaying the $10M SOC.
