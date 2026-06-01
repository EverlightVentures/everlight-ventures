# Everlense -- Photo & Screenshot Organizer

**Design spec** | 2026-05-31 | Everlight Ventures
**Status:** Approved (design), pending spec review then implementation plan
**Inspired by:** CompanyCam (per-job photo organization), adapted to a free, local, phone-first stack.

---

## 1. One-line

A local, $0, CompanyCam-style organizer that pulls photos and screenshots off the
camera roll and files them automatically: property photos by **job site**, personal
photos by **date**, and screenshots by **topic** (Linux / AI / Tech / Finance / ...),
with searchable metadata so any shot is findable in seconds.

## 2. Why (purpose)

- Camera roll today: **472 camera photos**, **1,177 screenshots**, plus social-app dumps.
- No organization, so photos are lost the moment they're taken and screenshots are a junk drawer.
- Business value: wholesale job-site photos tied to a property = documentation/proof for
  buyers and sellers ("photo taken 5/31 at 123 Main St"). Screenshots become a searchable
  knowledge pile (Linux how-tos, AI prompts, market shots).

## 3. Locked decisions (operator-approved 2026-05-31)

| Decision | Choice |
|---|---|
| Structure | **Hybrid**: `Personal/` + `Business/`; under Business -> property folders (job sites) + venture folders for non-site shots |
| Scope | **Both**: one-time backfill of ~1,650 + ongoing auto-organize |
| Screenshots | **Topic-sorted** (AI / Linux / Tech_Dev / Finance_Trading / RealEstate_Wholesale / Reference_HowTo / Receipts_Docs / Social / Memes / Personal), editable taxonomy |
| Location | **Both**: per-photo EXIF GPS (native camera location toggle ON) + project address (geocoded) |
| Tagging | **AI-assisted two-tier**: free heuristic/OCR first, Claude Haiku only on ambiguous |
| Watermark | **Yes, optional per project**: stamp a copy, keep clean original |
| Storage | **Phone folders only**, no cloud; under `04_MEDIA_LIBRARY/Photos/` (already git-ignored) |
| Name | **Everlense** (CLI `everlense`, alias `lens`) |

## 4. Hard constraints discovered (prove-real findings)

- **Termux:API is non-functional on this device** (Play Store Termux build): `termux-location`
  and `termux-camera-photo` have no backend, so **no programmatic GPS, no programmatic capture.**
  Capture is the *native camera*; GPS comes from EXIF (camera location toggle) + project address.
- **Phone proot cannot `npm/pnpm install`** (SIGSEGV, HARD LAW). Everlense is **pure Python** + apt
  packages. No Node anywhere.
- `04_MEDIA_LIBRARY/` is **git-ignored**, so photos and the index DB never enter git. Honors "phone-only."
- **Termux:Widget** `.shortcuts` dir exists, so a one-tap "Tag" button is feasible (verify app installed at build).
- Confirmed present: `Pillow 12.2.0`, `exifread`. To install at build: `tesseract-ocr` (apt), `pytesseract`,
  `anthropic` (Haiku classification), optional `reverse_geocoder`.

## 5. Folder taxonomy

All under `/mnt/sdcard/AA_MY_DRIVE/04_MEDIA_LIBRARY/Photos/` (git-ignored, rsync-excluded):

```
Business/
  Properties/
    2026-05_123-Main-St_Memphis-TN/          # project slug = YYYY-MM_<address-slug>_<city-state>
      IMG_20260531_143012.jpg
      IMG_20260531_143012.json               # sidecar metadata (see section 7)
      _stamped/IMG_20260531_143012_stamped.jpg   # optional watermark copy
  _Inbox/                                    # new camera shots awaiting project assignment
  Broker_OS/ Wholesale/ Content/ XLM/ ...    # venture folders (non-site business shots)
Personal/
  2026/
    05_May/
Screenshots/                                 # sorted by TOPIC (config-driven, editable)
  AI/ Linux/ Tech_Dev/ Finance_Trading/ RealEstate_Wholesale/
  Reference_HowTo/ Receipts_Docs/ Social/ Memes/ Personal/ _Inbox/
Social/                                      # WhatsApp/IG/FB dumps, parked as-is
_Trash/                                      # 14-day quarantine before original deletion
.everlense/                                  # state + index live here
  photos_index.db   categories.yaml   projects.json   state.json   classifier_rules.yaml
```

A `.nomedia` file is written into every destination folder so Android's gallery stops
indexing them. This is the "off the camera roll" mechanic.

## 6. Architecture -- 9 isolated modules

Each is a small, single-purpose unit with a clear interface. Pipeline order:
**Scan -> Classify -> Tag -> File -> Stamp -> Index -> Find**, plus Config and Runner.

1. **scanner.py** -- `scan(sources) -> list[MediaItem]`. Walks `DCIM/Camera`, `DCIM/Screenshots`,
   `Pictures/*`. Computes SHA-256 (dedupe), detects `source` (camera | screenshot | social),
   reads EXIF (datetime, GPS), skips already-indexed hashes. No mutation.
2. **classifier.py** -- `classify(item, profile) -> Label{category, project?, confidence, tier, source_signals}`.
   Two profiles:
   - `camera`: Tier-0 = EXIF/source/dimension heuristics -> Personal vs Business guess; Tier-1 = Claude
     Haiku vision on ambiguous (house exterior -> property; receipt -> Business/Receipts; selfie -> Personal).
   - `screenshot`: Tier-0 = **OCR (tesseract) + keyword rules** from `categories.yaml`
     (`sudo/apt/bash/$` -> Linux; `ChatGPT/Claude/prompt/model` -> AI; tickers/`$`/P&L -> Finance);
     Tier-1 = Claude Haiku (text-only, fed OCR) on low-confidence. Can propose a NEW category.
3. **tagger.py** -- interactive batch confirm (terminal + Termux:Widget). Shows AI suggestion + thumbnail
   path; operator accepts/corrects. Confirmed corrections append to `classifier_rules.yaml` (learning loop).
4. **filer.py** -- `file(item, label) -> dest_path`. **copy -> verify hash -> remove original**, original
   first moved to `_Trash/` (14-day window, reversible). Writes `.nomedia` to dest. Idempotent.
5. **stamper.py** (optional) -- `stamp(path, fields) -> stamped_path`. Pillow draws
   date / time / address / GPS in a corner band on a *copy* into `_stamped/`. Per-project toggle in `projects.json`.
6. **indexer.py** -- SQLite FTS5 `photos_index.db`: `(hash, path, source, category, project, taken_at,
   gps_lat, gps_lon, address, ocr_text, tags, stamped, created_at)`. `upsert(record)`, `search(query)`.
7. **finder.py** -- `everlense find "<query>"` matches project/address/category/date/OCR text.
   Optional `everlense gallery` generates a static HTML gallery served on `127.0.0.1` (network doctrine).
8. **config.py** -- loads/validates `categories.yaml` (screenshot topics + keyword rules),
   `projects.json` (properties: slug, address, geocoded lat/lon, watermark on/off), `state.json` (scan cursor).
9. **everlense (CLI) + runner** -- subcommands: `scan`, `tag`, `backfill`, `find`, `gallery`,
   `project add`, `categories`. Termux:Widget `.shortcuts/everlense-tag` button -> `everlense scan && everlense tag`.
   Optional cron auto-files only high-confidence items; ambiguous queued for `tag`.

## 7. Sidecar metadata (per photo, JSON next to the file)

```json
{
  "hash": "sha256:...",
  "source": "camera",
  "original_path": "/sdcard/DCIM/Camera/20260531_143012.jpg",
  "taken_at": "2026-05-31T14:30:12-07:00",
  "category": "Business/Properties",
  "project": "2026-05_123-Main-St_Memphis-TN",
  "address": "123 Main St, Memphis, TN",
  "gps": {"lat": 35.1495, "lon": -90.0490, "from": "exif"},
  "tags": ["exterior", "roof"],
  "ocr_text": null,
  "stamped": true,
  "classified_by": {"tier": 1, "model": "claude-haiku-4-5", "confidence": 0.86},
  "filed_at": "2026-05-31T14:35:02-07:00"
}
```

Sidecars are the human-readable truth; `photos_index.db` is the fast query layer rebuilt from sidecars.

## 8. Location handling ("both")

- **Per-photo GPS:** read from EXIF when present. Operator flips the **native camera location toggle ON**
  (documented one-time step), so new shots carry real coords. Backlog (GPS off) has no per-photo coords.
- **Project address:** every Business property has an address, geocoded **once** via free
  OpenStreetMap Nominatim (1 req/s, cached in `projects.json`). Address is the always-present location label.
- Backlog property photos: no GPS, but inherit the project address once tagged.

## 9. Backfill plan (one-time, ~1,650 items)

1. **Screenshots (1,177)** -> OCR + keyword rules auto-sort the clear majority for $0; ambiguous -> Haiku;
   truly unclear -> `Screenshots/_Inbox/`.
2. **Social dumps** -> parked in `Social/<app>/` untouched.
3. **Camera photos (472)** -> Haiku suggests Personal vs Business; operator confirms projects in a batch.
   Old shots with unknowable project -> `Business/_Inbox/` for a quick manual pass.
4. Everything goes through `_Trash/` (14-day), so **no deletion without the quarantine window** (verify-before-destroy).

## 10. FREE-FIRST cost ledger

| Component | Cost |
|---|---|
| scanner, OCR (tesseract), filer, stamper, indexer, finder, gallery, widget | **$0** (offline) |
| Nominatim geocoding | **$0** (free tier, occasional manual property adds) |
| Tier-1 AI classification | Anthropic **Haiku**, pennies, only on ambiguous items; OpenRouter fallback available |
| Storage | **$0**, local phone folders, no cloud |

Only non-free element is Tier-1 Haiku on ambiguous items, clearly labeled. Everything else is free/offline.

## 11. Risks & mitigations

- **Mis-move loses a photo** -> copy+verify-hash before any delete; originals to `_Trash/` 14 days; idempotent filer.
- **Termux:Widget not installed** -> CLI works standalone; widget is a convenience, verified at build.
- **OCR misfires** -> low-confidence falls through to AI; operator corrections train the rule file.
- **Index/sidecar drift** -> index is rebuildable from sidecars (`everlense reindex`); sidecars are source of truth.
- **Photo store bloating sync** -> confirm `04_MEDIA_LIBRARY/` excluded from e5/AceMagician rsync (git already excludes).

## 12. Non-goals (YAGNI)

- No cloud upload, no Immich, no mobile app, no face recognition, no video organization (photos+screenshots only).
- No programmatic camera capture (device can't; native camera is the capture tool).
- No multi-user / sharing.

## 13. Testing

- Unit: classifier rules (fixture screenshots -> expected category), filer idempotency + hash-verify,
  sidecar round-trip, index search.
- Integration: backfill dry-run mode (`--dry-run` prints planned moves, touches nothing) before any live move.
- Manual: tag-flow on 10 real photos; confirm gallery + `find` return correct results; confirm `.nomedia`
  removes folder from gallery.

## 14. Rollback

`_Trash/` holds originals 14 days. `everlense restore <hash|date>` moves files back to `DCIM`. Index/sidecars
are additive; deleting `.everlense/` resets state without touching photos. The whole tree is git-ignored, so
no repo impact.
