# Slack Org Infrastructure

This package provisions channels and provides reusable logging for a multi-agent Slack org.

## What It Includes

- `config/channel_map.json`: Channel map for war room + agent teams.
- `config/task_schema.json`: Standard task object schema.
- `config/template_*.txt`: Exact Slack message templates.
- `slack_api.py`: Slack Web API wrapper with retry and failure logging.
- `channel_registry.py`: Loads channel map and stores channel ID registry.
- `logger.py`: Reusable logger module with per-task thread routing.
- `scripts/create_channels.py`: Creates or connects channels from map.
- `examples/example_usage.py`: Example logger usage.

## Environment Setup

1. Copy values from `.env.example` into your environment.
2. Set `SLACK_BOT_TOKEN` (required for `conversations.create` and `chat.postMessage`).
3. Optional: set `SLACK_SIGNING_SECRET` if you later add event handlers.

## Create or Connect Channels

```bash
cd /mnt/sdcard/AA_MY_DRIVE
python3 -m everlight_os.slack_org.scripts.create_channels
```

Dry run:

```bash
python3 -m everlight_os.slack_org.scripts.create_channels --dry-run
```

This writes resolved channel IDs to:

- `config/channel_registry.json`

## Use Logger in Agents

```python
from everlight_os.slack_org.logger import SlackLogger

logger = SlackLogger()
logger.post_agent_log(
    channel="book_team.book_showrunner",
    task_obj=task_obj,
    actions=["..."],
    decisions=["..."],
    blockers=["..."],
    artifacts=["..."],
)
logger.post_war_room_update(task_obj, summary="...")
```

## Available Logger Functions

- `post_agent_log(channel, task_obj, actions, decisions, blockers, artifacts)`
- `post_war_room_update(task_obj, summary)`
- `post_thread_update(channel, thread_ts, text)`
- `post_approval_request(channel, payload)`
- `post_escalation(channel, payload)`

## Threading Model

Each `task_id` gets one parent thread in:

- agent channel
- `#ai-war-room`

Thread IDs are persisted in:

- `config/task_threads.json`

## Failure Handling

- API calls use exponential backoff retry.
- Failures are logged to `config/slack_failures.jsonl` with UTC timestamp and reason.
- Non-post failures attempt an alert to `#agent-errors` once registry IDs exist.
