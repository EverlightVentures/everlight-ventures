# Hive Logger API

One chokepoint. Every bot run goes through it. Every artifact lives in one
searchable place.

## Why this exists

Before this module, bot activity landed in three incompatible places:

1. Scattered `.jsonl` files per bot, never centralized.
2. Blinko notes posted by 11 different code paths with inconsistent tags.
3. Google Doc URLs that lived only in one-off Slack messages.

Result: the `:8504` dashboard showed stale activity, and the team could not
find a doc a bot created two weeks ago without grepping Slack history.

Hive Logger fixes both by forcing every bot through a single canonical log
line that writes to three sinks at once.

## Public API

```python
from content_tools import hive_logger

run = hive_logger.start(
    agent="rex_wholesale",      # max 64 chars
    task="monday-pipeline-run", # max 255 chars
    inputs={"lead_count": 42},  # any dict, will be redacted
    tags=["#hive/wholesale"],   # validated against hive_tags.VALID_TAGS
)

# Structured events during the run (optional)
run.event("lead.ingested", {"id": 123})

# Register every artifact the bot creates
run.artifact(
    kind="gdoc",                # gdoc | html | file | slack_post | blinko_note | supabase_row
    url="https://docs.google.com/document/d/...",
    title="Monday Pipeline Report",
)

# End the run (always call this, even on failure)
run.finish(
    status="done",              # done | partial | failed
    summary="Processed 42 leads, matched 7 to buyers.",
)
```

## Sink order and failure semantics

`run.finish()` writes to three sinks in this order:

1. **Local JSONL** at `_logs/hive_runs/events.jsonl`. Always written. This is
   the source of truth if the network is down.
2. **Django endpoint** `POST :8504/api/logger/ingest/`. Upserts `HiveSession`
   and creates `HiveArtifact` rows. Swallows errors, logs to
   `_logs/hive_runs/errors.jsonl`.
3. **Blinko upsert** `POST :1111/api/v1/note/upsert`. Creates a searchable note
   with artifact links. Swallows errors.

A failure in any sink is logged to `errors.jsonl` but never raises. A logging
failure never aborts a bot.

## Canonical log line schema

```json
{
  "session_id": "uuid4-hex",
  "agent": "rex_wholesale",
  "task": "monday-pipeline-run",
  "status": "done",
  "mode": "full",
  "started_at": "2026-04-24T14:00:00+00:00",
  "finished_at": "2026-04-24T14:02:31+00:00",
  "duration_seconds": 151.2,
  "summary": "Processed 42 leads, matched 7.",
  "routed_to": ["claude"],
  "events": [
    {"ts": "...", "session_id": "...", "agent": "...", "type": "lead.ingested", "payload": {}}
  ],
  "artifacts": [
    {"kind": "gdoc", "title": "...", "url": "...", "path": "", "tags": []}
  ],
  "tags": ["#hive/wholesale"],
  "inputs_redacted": {"lead_count": 42},
  "redactions_applied": 3
}
```

## Redaction

`summary`, `inputs`, and `event.payload` string values are passed through a
regex pipeline that replaces:

- Email addresses  ->  `<redacted-email>`
- Phone numbers    ->  `<redacted-phone>`
- Bearer tokens    ->  `<redacted-token>`
- `api_key = ...`  ->  `<redacted-key>`
- AWS access keys  ->  `<redacted-aws>`
- Stripe live/test keys ->  `<redacted-stripe>`
- Supabase keys    ->  `<redacted-supabase>`
- Slack tokens     ->  `<redacted-slack>`

A running `redactions_applied` counter is included in the canonical line so
false-positive rate is observable. Tighten patterns if the counter spikes.

## Auth (optional)

If `HIVE_LOGGER_TOKEN` is set in the Django settings or env, the ingest
endpoint requires the header `X-Hive-Token: <token>`. When unset, the
endpoint is open (the expected Phase A state before secrets are rotated in).

## Config via env

| Variable              | Default                              | Purpose                          |
|-----------------------|--------------------------------------|----------------------------------|
| `HIVE_DASHBOARD_URL`  | `http://127.0.0.1:2200`         | Where to POST the canonical line |
| `HIVE_LOGGER_TOKEN`   | *(unset)*                            | Shared secret for the endpoint   |
| `BLINKO_URL`          | `http://163.192.19.196:1111`         | Blinko upsert target             |
| `BLINKO_TOKEN`        | *(unset)*                            | Blinko auth, if configured       |

## Auto-artifact from `hive_3format.publish()`

`hive_3format.publish()` calls `hive_logger.current_run()` internally. If a
run is active, every successful `publish()` auto-registers a `gdoc` and `html`
artifact. No caller code change required once Phase B lands.

## Artifact search

```
GET :8504/api/artifacts/search/?kind=gdoc&q=monday&since_days=14&limit=50
```

Query params:

- `kind`       -- filter by artifact kind (gdoc, html, file, slack_post, blinko_note)
- `agent`      -- filter by agent name
- `q`          -- substring match on title / url / path
- `since_days` -- restrict to artifacts created in the last N days
- `limit`      -- 1 to 500, default 50

Response:

```json
{
  "ok": true,
  "count": 12,
  "results": [
    {
      "id": 41,
      "kind": "gdoc",
      "agent": "rex_wholesale",
      "title": "Monday Pipeline Report",
      "url": "https://docs.google.com/...",
      "path": "",
      "tags": ["#hive/wholesale"],
      "created_at": "2026-04-24T14:02:31+00:00",
      "session_id": "abc123..."
    }
  ]
}
```

## Selftest

Run from any host with workspace access:

```
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/hive_logger.py --selftest
```

Expected result within 60 seconds:

- `:8504/admin/hive/hivesession/` shows a new row with `agent=smoke-test`.
- `:8504/api/artifacts/search/?agent=smoke-test` returns the dummy artifacts.
- `curl :1111/api/v1/note/list -H "Content-Type: application/json" -d '{"searchText":"smoke-test","size":5}'` returns the note.

## Controlled tag vocabulary

See `hive_tags.py`. Use `VALID_TAGS` constants. Unknown tags are remapped to
`#hive/uncategorized` with a stderr warning. Add new tags to the set only
after the team agrees.

## Rollout phases

- **Phase A** (done once this module ships): utility + endpoints live, no bots wired.
- **Phase B**: wire `hive_3format.publish()` + top 4 bot entry points.
- **Phase C**: update agent prompts + enable weekly index regen + enable retention cron.
