# Slack War Room - XLM Bot Agent Debates

## Goal
Connect the XLM bot's live agent communication (agent_comms.py) to a
dedicated Slack channel so the user can observe Claude, Gemini, and Codex
debating trades in real-time.

## Current State
- `ai/agent_comms.py` writes to `data/agent_comms.json` (local file only)
- `alerts/slack.py` posts trade alerts via webhook (already working)
- `everlight_os/slack_org/` has a full Slack infrastructure but is NOT
  connected to the XLM bot and uses a different Bot Token API (not webhook)
- Webhook URL is already configured in config.yaml

## Plan

### Step 1: Add war room webhook to config.yaml
Add a second webhook URL field under `slack:` for the war room channel.
If user only has one webhook, we'll reuse the existing one with a
`[WAR ROOM]` prefix to distinguish messages.

Config addition:
```yaml
slack:
  war_room_webhook_url: ""   # separate channel, or leave blank to use main webhook
```

### Step 2: Add war room posting functions to alerts/slack.py
New functions (fire-and-forget, same pattern as existing alerts):
- `war_room_assessment(agent_name, assessment)` - when an agent posts its view
- `war_room_debate(challenger, defender, summary)` - challenge round exchange
- `war_room_consensus(result)` - final consensus reached
- `war_room_entry(signal, consensus)` - trade entered with agent agreement info
- `war_room_exit(result, consensus)` - trade exited with agent views

Uses rich Slack block formatting (headers, sections, context) for readability.

### Step 3: Wire agent_comms.py to Slack
Add Slack posting calls inside:
- `post_assessment()` - after writing to JSON, also post to Slack
- `log_consensus()` - after logging, also post consensus to Slack
- `check_exit_challenge()` - post challenge alerts to Slack

### Step 4: Wire main.py exit/entry paths
After the existing `slack_alert.trade_entry()` and `slack_alert.trade_exit()`
calls, add war room posts that include which agents agreed/disagreed and why.

## Files Modified
1. `config.yaml` - add war_room_webhook_url
2. `alerts/slack.py` - add 5 war room functions
3. `ai/agent_comms.py` - add Slack calls in post_assessment, log_consensus
4. `main.py` - add war room posts at entry/exit points

## Risk
- Zero: all Slack posts are fire-and-forget in background threads
- Bot never blocks or crashes on Slack failures
- Uses existing working webhook pattern
