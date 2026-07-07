# Solano Live Desk -> Personal SecOps (PSIM) Upgrade Spec

**Date:** 2026-07-07
**Owner:** Rich Gee (operator) / Lucrex (build)
**Supersedes:** the roadmap section of `2026-07-07-solano-live-desk-design.md` (Phase 1 stays as built)
**Status:** Approved vision, pre-implementation, pending ONE decision (SDR linchpin, Section 10)

---

## 1. What this becomes

A personal Physical Security Information Management system (PSIM) modeled on AMAG
Symmetry / a corporate SOC console, tuned to one operator who lives mobile (car + phone).
It fuses four signal types into ONE prioritized alarm queue centered on the question
"is anything near me a threat to me and my family right now":

- **Incidents** (structured text: CHP, weather, fire/EMS CAD) -> the map + the alarms
- **Scanner audio** (live-listen; auto-transcribed only with the optional SDR) -> criminal/pursuit color
- **Cameras** (public traffic cams + future own cams) -> visual verification of the audio/incident
- **Your GPS** (own device) -> proximity, heading, "how often am I here", follow-me

It follows you: as you drive into a new county, it auto-detects the county and re-keys the
local scanner list + incident feeds + cameras for wherever you are.

## 2. Non-negotiable guardrails (from CA counsel research, hard lines)

- **NO license-plate reading / ALPR, ever.** CA Civ. Code 1798.90.5 / SB 34 makes a private
  individual running ALPR an "ALPR operator" with public policy-posting duties and a private
  right of action (1798.90.54, plaintiffs can sue). No plate OCR, no plate strings stored.
  "How often is MY car here" comes from MY GPS; "how busy is an area" comes from ANONYMOUS counts.
- **NO decrypting encrypted radio.** Federal "you may listen" covers UNENCRYPTED only.
  When a channel encrypts (P25), we drop it, never attempt to break it.
- **NO using intercepts to evade/obstruct police** (CA PC 636.5). Safety awareness only.
- **NO tracking of identifiable third parties.** Anonymous aggregate counts only (stalking/
  privacy exposure otherwise).
- **NO scraping/restreaming Broadcastify audio** (their ToS). Live-listen embeds only.
  Auto-transcription uses OUR OWN receiver (SDR), which is lawful (18 USC 2511(2)(g)(i),
  47 USC 605 mere-interception; PC 632 excludes radio).
- **Minimize at ingest:** counts over images; keep snapshots only on real incidents; short
  retention; local + encrypted; bind 127.0.0.1 (tailnet only). Keep a one-page purpose note.
- Not legal advice; a 30-min CA privacy-attorney bless of the final architecture is cheap insurance.

## 3. Verified free source stack (the follow-me layer)

| Source | Endpoint | Gives | Coverage | Verified |
|---|---|---|---|---|
| GPS -> county | `geo.fcc.gov/api/census/block/find?latitude=&longitude=&format=json` | County FIPS + name (the re-key trigger) | Nationwide | Y |
| CHP incidents (primary) | `media.chp.ca.gov/sa_xml/sa.xml` | dispatch log + coords (Phase 1 backbone) | CA highways | Y (in prod) |
| CHP incidents (backup) | `quickmap.dot.ca.gov/data/chp-only.kml` | ~80 statewide incidents, simpler | CA highways | Y |
| Weather/hazard | `api.weather.gov/alerts/active?point=LAT,LON` | NWS alerts, severity, polygons | Nationwide | Y |
| Earthquakes | `earthquake.usgs.gov/.../all_hour.geojson` | quakes near point | Nationwide | Y |
| Fire/EMS CAD | `web.pulsepoint.org/DB/giba.php?agency_id=NNN` | incident type + lat/lon (AES JSON, reverse-eng) | ~5,500 agencies incl. Solano | corroborated, ToS-gray |
| Scanner LIST (not audio) | `broadcastify.com/listen/ctid/CTID` | county feed names/IDs to tap-listen | Nationwide | Y |

Dead ends (documented, not used): Broadcastify Catalog API ($2,500/mo), Citizen (metro-only +
ToS), Waze georss (403/ToS), IPAWS (registration-gated), no free nationwide LE CAD feed.

**The LE gap:** no free structured real-time LAW-ENFORCEMENT feed exists. Criminal activity
(the "Kansas City inmate pursuit") lives on scanner AUDIO. Auto-detecting it needs transcription
-> that is the SDR linchpin (Section 10). Without SDR, LE awareness = live-listen tray + whatever
pursuit hits CHP (many do).

## 4. Camera + computer-vision reality (measured, not assumed)

Caltrans cams are **320x240 / 352x240 (CIF)**. That hard-caps CV:

- **Shippable (reliable):** vehicle/person presence + class, coarse vehicle COUNTS, a
  congestion/occupancy score (free-flow vs slow vs jammed), and **stopped-traffic detection**
  (compare 2-3 snapshots; near-identical blobs = stopped = strong incident proxy).
- **Hint-only (labeled low-confidence):** night-time "possible emergency lights" flicker,
  "something changed here" motion.
- **Impossible (physics):** license plates (~2-4px), face/vehicle ID, make/model, reliable
  animal ID, confident emergency-vehicle classification, per-object direction from snapshots
  (direction is already in the camera label like `E80`/`N680`).
- **Stack (e5 ARM CPU, no GPU):** YOLO11n exported to ONNX, run at 320px via onnxruntime
  (~40-70 ms/frame, <10% of one core at 1 frame / 2-5s -> can poll dozens of cams). Roboflow
  Supervision (MIT) for counts/zones. Permissive alt to avoid AGPL: YOLOX-nano / MobileNet-SSD.
  Frame grab = poll the JPEG (default) or ffmpeg short burst from HLS on demand. Never hold
  streams open.
- **Use pattern (the "visual support for audio"):** incident fires with lat/lon -> find nearest
  Caltrans cams from the D4 JSON -> pull snapshots -> YOLO -> emit "3 cams near incident:
  I-80 @ Air Base Pkwy shows heavy stopped traffic (~15 veh, congestion HIGH)."
- **Phone-as-dashcam (future roving eye):** periodic snapshot every 2-5s (NOT full video);
  on-device TFLite MobileNet best, or ship frames to e5. ~20-40 MB/hr. Optional, later.

## 5. Threat-classification engine (rules first, Haiku on the margin)

Two axes multiplied: **severity** (what happened) x **proximity/heading** (how close, coming toward me).

- **Severity from keywords/codes** (free): CRITICAL = shots fired / 11-99 / 245 ADW / 207 /
  211 armed / active pursuit / wrong-way / structure fire; HIGH = injury collision / vehicle
  fire / hazmat / wires down; MEDIUM = medical / alarm / person down; LOW = property-damage
  collision / traffic hazard / assist / animal / debris.
- **Proximity** (Haversine from my GPS): IMMEDIATE <0.5mi, NEAR 0.5-2mi, AREA 2-5mi, REGIONAL >5mi.
- **Heading modifier:** pursuit/fire bearing within +/-45 deg of me -> +1 escalation ("coming my way").
- **Matrix -> threat level:**

```
                 IMMEDIATE   NEAR      AREA      REGIONAL
CRITICAL         EXTREME     EXTREME   HIGH      MEDIUM
HIGH             EXTREME     HIGH      MEDIUM    LOW
MEDIUM           HIGH        MEDIUM    LOW       LOW
LOW              MEDIUM      LOW       LOW       (log only)
```

- **Haiku only on ambiguous/near events** (~$0.001/call, prompt-cached): disambiguate scanner
  transcripts (negations/homophones), geocode fuzzy locations, judge heading intent, one-line
  the alarm title, dedupe the same event arriving from CHP + PulsePoint + scanner.
  Strict JSON out; the deterministic matrix makes the final call, not the model.

## 6. Alerting stack (all free, ARM64)

- **ntfy** self-hosted on e5 = phone push, 5 priority tiers, breaks Do-Not-Disturb on high/urgent,
  carries a camera SNAPSHOT + a deep-link "OPEN" button (alarm-to-video from the lock screen).
- **Apprise** (BSD-2) = router with tag-priority escalation/failover.
- **branded_mailer** = email (mandatory path, gold template, budget-gated), `budget_category="system"`.
- **Dashboard WebSocket** = in-app live push.
- **Routing:** EXTREME -> ntfy urgent + email + auto-pull cameras/60s clip/scanner-priority +
  incident-takeover UI; HIGH -> ntfy high + email + 15s clip; MEDIUM -> hourly digest;
  LOW -> daily digest / log only. Escalation net: if ntfy publish fails, fall back Gotify -> email,
  so an imminent-danger alert can never be silently dropped.

## 7. DVR / memory

- SQLite (WAL) for records + flat files for media, foldered `media/YYYY/MM/DD/<threat>/<category>/<zone>/<incident_id>/`.
- Tables: `incidents, events (audit log), snapshots, clips, cv_detections, gps_track, alerts`.
- Capture: ffmpeg snapshot + short clip from cam on event; snapshot-every-5s on EXTREME.
- Retention cron on e5: EXTREME 365d, HIGH 90d, MEDIUM 30d, LOW 7d, GPS 90d, CV 14d; archive
  EXTREME/HIGH after-action JSON before any purge (no-deletion doctrine).

## 8. PSIM dashboard (AMAG-style)

Single self-hosted page on e5 (FastAPI + WebSocket), 6 regions:
- **A Status bar:** threat posture GREEN/YELLOW/ORANGE/RED, zone, live GPS, feed health, unacked count.
- **B Alarm queue (heart):** uncleared alarms sorted threat DESC, distance ASC; color band per level.
- **C Map:** my pin + proximity rings (0.5/2/5 mi), incident pins by threat, heading vectors.
- **D Video/verification:** click alarm -> nearest camera live + snapshot captured at event time.
- **E Live event log:** every event incl. auto-handled (audit trail).
- **F Case/SOP workflow:** one yes/no SOP step, Acknowledge / Note / Escalate / Clear -> after-action row.
- **Incident-takeover mode:** EXTREME collapses UI to Map + Video + the one SOP question, full screen.
- Categorized email: subject `[SECOPS][THREAT][category] one-liner (distance)` -> Gmail labels.

## 9. What we will NOT build (honest ceilings)

ALPR / plate capture (legal + physics) · PTZ/panning of public cameras (not exposed) · scraping
Broadcastify audio (ToS) · decrypting encrypted agencies · realtime multi-cam video analytics
(no GPU; event-driven snapshots instead) · tracking identifiable people/vehicles.

## 10. THE ONE DECISION: the $30 SDR linchpin

Auto-detecting a police PURSUIT / criminal call (your inmate example) requires transcribing
LOCAL police audio. There is NO free, no-hardware, legal path for Solano (OpenMHz empty,
Broadcastify listen-only). A ~$30 RTL-SDR receiver is legal (own-receiver interception of
unencrypted radio) and unlocks it 100%: local audio -> whisper.cpp on e5 -> threat engine ->
auto-alert. It does NOT plug into your phone; it rides as a small standalone node (in the car
off USB, or at a fixed spot you can access) and can follow you.

- **Without SDR:** full system minus auto-audio-detection. LE awareness = live-listen tray
  (your ear) + pursuits that hit CHP. Still a huge, real safety tool.
- **With SDR:** the system HEARS and auto-alerts on pursuits/shots-fired/etc. near you. This is
  the difference between "I hope I catch it" and "it caught it and pushed my phone."

## 11. Re-scoped roadmap (each a shippable increment)

- **Phase 1 (DONE):** live CHP incident map, corridor scope, timeline, archive.
- **Phase 2A -- Follow-me + threat engine:** GPS->county re-key, add NWS + USGS + PulsePoint +
  CHP-KML backup, Broadcastify follow-me listen tray, the severity x proximity x heading threat
  matrix. Output: incidents ranked by danger-to-me on the map.
- **Phase 2B -- Alerts + DVR:** ntfy + Apprise + branded_mailer routing by threat level, SQLite
  DVR + media capture + retention, categorized email/labels.
- **Phase 2C -- Eyes:** Caltrans camera auto-pull near incidents + YOLO11n-ONNX congestion/
  presence "visual support for the audio". Broadcastify live-listen embeds per zone.
- **Phase 3 -- PSIM dashboard:** the 6-region AMAG-style console + incident-takeover + case/SOP + reports.
- **Phase 4 -- SDR audio (if chosen):** RTL-SDR node -> whisper.cpp -> auto threat detection on
  local police audio. The roving scanner that follows you.
- **Phase 5 (optional) -- Phone-as-dashcam roving eye:** periodic on-device detection.

**Reuse/tools:** onnxruntime + YOLO11n/YOLOX + Supervision (CV); ntfy + Apprise + Gotify
(alerts); Frigate + MediaMTX/go2rtc (if real cameras later); whisper.cpp (SDR audio);
FCC/NWS/USGS/QuickMap/PulsePoint (feeds). All free/permissive except Haiku (~$0.001/call).
