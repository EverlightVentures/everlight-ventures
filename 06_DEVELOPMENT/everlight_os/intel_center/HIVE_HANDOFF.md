# Everlight Intel Center -- Hive Handoff (Phase 6+)

**Status:** Phases 1-5 of MVP shipped 2026-05-11.
**Owner of Phases 6-10:** Hive — Marcus dispatches; named agents below own each lane.

## What's already built (don't redo)

```
/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center/
├── build_intel_db.py                    # full pipeline, idempotent
├── config/categories.yaml               # 20 categories, ~600 hints, TLD overrides
├── extracted/raw_ocr/         (64 .txt) # cached OCR text -- never re-OCR
├── extracted/parsed/          (64 .json)# parsed candidates per photo
├── database/
│   ├── everlight_resources_master.csv   # 730 rows, 25 cols
│   ├── everlight_resources_master.json  # same data, JSON
│   ├── everlight_resources.sqlite       # indexed by category/domain/agent
│   └── resource_review_queue.csv        # 80 rows needing eyes
└── guides/everlight_resources_master.html  # branded gold-on-dark index
```

**Re-run cost:** 1.2s with `python3 build_intel_db.py --no-ocr` (cache hit).
**First-run cost:** ~35min (one-time OCR of 64 photos).

## Resource counts by category

| # | Category | Department | Agent owner |
|---|---|---|---|
| 181 | Decision Intelligence | CEO Command Center | Strategic Modeler |
| 165 | OSINT & Investigation | OSINT Desk | Cipher Wolfe |
| 93 | Education & Training | CEO Command Center | Strategy Assistant |
| 59 | Self-Hosting & Privacy | DevOps Desk | Engineering Foreman |
| 59 | Trading & Finance | Trading Desk | Bull Archer |
| 37 | Content Creation | Content Engine | Listing Writer |
| 35 | Health & Environment | Disaster Response Desk | Helix Patel |
| 28 | Space & Science | CEO Command Center | Helix Patel |
| 24 | News & Journalism | Everlight Newsroom | Wire Santos |
| 24 | Weather & Disaster Intel | Disaster Response Desk | Helix Patel |
| 12 | Maps & Geospatial | OSINT Desk | Cipher Wolfe |
|  7 | AI & Automation | DevOps Desk | Nova Ling |
|  3 | APIs & Developer Tools | DevOps Desk | Engineering Foreman |
|  2 | eCommerce & Product Research | Product Desk | Pitch Adler |
|  1 | Real Estate & Property | Wholesale Desk | Rex Blackwell |
| **730** | **TOTAL** | | |

86% auto-categorized, 11% in review queue, 3% spreadsheet-vetted.

## Phase 6 — Streamlit dashboard (Engineering Foreman + Component Engineer)

**Source of truth:** `database/everlight_resources.sqlite`
**Pages required (per spec):** Home, Resource Search, News Center, OSINT Desk, Market Intel,
Disaster Watch, API Library, Content Tools, Agent Router, Compliance Log.

**Read-only patterns to copy:**
- Use `content_tools/report_template.py` palette (gold #D4A843, dark #0A0A0A) — same brand as the HTML report.
- SQLite query layer; do NOT load JSON into memory each page.
- Filter by `category`, `department`, `agent_owner`, `verified_status` chips.
- Resource cards: name, domain (link), purpose, agent owner badge, "copy prompt" button.

## Phase 7 — Slack `/intel` commands (Marcus + Cipher Wolfe)

**Channel:** `#hive-alerts` (charter allows command bot replies).
**Commands to implement (12 total):**
```
/intel search <topic>          → SQL LIKE on purpose + tags
/intel tool <task>             → search + return top 3 with agent recommendation
/intel news <region>           → category=News, optional region filter
/intel weather <location>      → category=Weather + suggest live source
/intel market <asset>          → category=Trading + macro link
/intel disaster <region>       → category=Weather/Disaster
/intel osint <task>            → category=OSINT + legal_notes warning
/intel product <market>        → category=eCommerce
/intel api <capability>        → category=APIs
/intel briefing daily          → top 5 per category for CEO
/intel verify <url>            → live HEAD check + last_checked update
/intel add-resource <url notes> → INSERT INTO sqlite + flag review
```

Wire through existing Slack bot in `06_DEVELOPMENT/everlight_os/hive_mind/slack_routing.yaml`.

## Phase 8 — n8n / cron briefings (Marcus + Strategic Modeler)

n8n is **PARKED**. Use Oracle cron + `content_tools.publish_gdoc()` instead:
- Daily 7 AM PT CEO brief: top 5 unread/recent resources per priority category.
- Weekly resource refresh: re-run `build_intel_db.py` if new images dropped in `FREE RESOURCES/Photos/`.
- Monthly review-queue digest: post `resource_review_queue.csv` to `#war-room`.

Cron lives on Oracle (per Operator Truth Doctrine — phone is never a cron host).

## Phase 9 — Vector search (Nova Ling + AI Integration Lead)

**Why:** Keyword search fails on intent ("find me something to deal with a hurricane forecast"
won't hit `weather` if user says `cyclone`). Vector embeddings on `purpose + raw_text` solve this.

**Recommended stack:** sentence-transformers `all-MiniLM-L6-v2` → sqlite-vss extension or simple
numpy cosine sim (730 rows = trivial; no Pinecone needed).

**Index file:** `database/vector_index/embeddings.npy` + `ids.json`.

## Phase 10 — Live source verification (Justine + Compliance Gate)

**Why:** A resource list rots fast. 64 of 730 are likely dead/redirected within 6 months.

**Pattern:**
- Weekly Oracle cron: HEAD-request every domain in batches of 50, with 5s timeout.
- 4xx/5xx → flip `verified_status` to `broken`, log to `logs/verification_<date>.jsonl`.
- 200 with redirect → update `url` field, leave domain.
- Update `last_checked` on every check.

## Review queue (80 rows) — manual triage

These are mostly API mega-list rows where the description was too generic, plus a few OCR
mangles. Suggested triage:
1. Open `database/resource_review_queue.csv`.
2. Delete rows where `domain` is obviously not a real site (OCR garbage).
3. For surviving rows, hand-set `category` + `agent_owner` and re-import.

## Self-improvement loop

When new ByteClave (or any source) screenshots drop in `FREE RESOURCES/Photos/`, the cycle is:
```
1. python3 build_intel_db.py             # OCR new files (cache hits skip old)
2. eyeball unique topic headers          # add new ones to categories.yaml hints
3. python3 build_intel_db.py --no-ocr    # re-categorize in 1.2s
4. SQLite tables + HTML report rebuild atomically
```

## Operator Truth disclosures

What I did NOT build this turn (per your spec, but punted to Phase 6+):
- Streamlit dashboard
- Slack `/intel` command bot
- n8n / cron briefings
- Vector search
- Live source verification
- Per-tool guides (`how_to_use_each_tool.md`)
- OSINT legal rules (`osint_legal_rules.md`) — only the YAML reference exists
- Agent playbook

What I DID build:
- 64 OCR text files (cached, never re-run)
- 64 parsed JSON candidates
- 730-row deduped categorized DB in 5 formats
- Branded HTML index at `guides/everlight_resources_master.html`
- 86% auto-categorized via word-boundary regex + photo-header inheritance
- Idempotent `--no-ocr` re-run path
- Hive handoff (this file)
