---
name: observability_first
description: When building any service, design metrics + dashboard alongside the code. Logs say what happened; metrics say is-it-healthy-now.
---

When to use:
- Any new Oracle service, n8n workflow, agent pipeline, or recurring cron.
- Any new user-facing UI feature (Lucrex OS, Django :8504, hivemind site).

The split:
- **Logs** answer "what happened on request X?" (debugging)
- **Metrics** answer "is the service healthy right now?" (monitoring)
- **Dashboard** lets a human see metrics without terminal access.

Required at ship time:
1. **Log line** -- canonical_log_line skill.
2. **Metric** -- counter for invocations + outcome breakdown, histogram for duration. Push to Django HiveArtifact + Blinko or Prometheus if available.
3. **Dashboard widget** -- visible on Lucrex OS or :8504. Three panels minimum: invocations/hour, error rate, p95 latency.
4. **Alert** -- one Slack message rule (channel #hive-alerts) for: error rate > 5% sustained 15 min OR no-invocation gap > 2x expected interval.

Hive-specific: every new dashboard widget gets a button ("Run skill", "Refresh") so non-engineer team members (and Marcus) can interact without opening the terminal -- per AIOS observability layer doctrine.

Output contract for every new service PR:
- Service code
- Log line (canonical)
- Metric emission
- Dashboard panel diff (Lucrex OS or :8504 view)
- Slack alert rule (file + channel)

If the PR is missing any of the four, it's not ready to ship. No exceptions.
