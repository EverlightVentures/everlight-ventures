# Monitoring Stack -- Deferred (2026-05-19)

## Decision

Defer Prometheus + Grafana build to a future session. No Everlight-side
scaffolding exists today. Building from scratch is a 3-day sprint.

## Why defer

Per `feedback_apply_macro_micro_gate_before_recommendation_list` and
`feedback_no_trash_until_deal1`:

- Prometheus + Grafana = monitoring + observability layer. Adds zero direct
  revenue, replaces the existing Streamlit/Django dashboards.
- Current observability is functional, not premium: Uptime Kuma (visual
  status), `_logs/*.jsonl` (structured logs), Slack `#hive-alerts` (signal).
- Stripe MCP escalation loop (caught this session) proves the basics work --
  it_triage IS firing, it_triage IS escalating, the alerts ARE landing in
  Slack. The bottleneck is closing the alert, not seeing it.
- Building Prometheus before Deal 1 funds the operation is macro drift.

## What we have today (good enough for Phase 1)

- `it_triage.py` cron every 1 min: queue-based remediation + escalation
- `_logs/*.jsonl` structured logs (http_client, branded_mailer, send_authority_gate, it_triage)
- Uptime Kuma: visual status board for services
- Slack `#hive-alerts`: real-time fail-loud signal per `feedback_fail_loud_with_it_auto_repair`
- Branded daily/weekly reports via `branded_slack` + `gdocs_bridge`

## Defer triggers (when to revisit)

- Deal 1 closes -> revenue funds the build
- >20 distinct services running -> Prometheus's value compounds with scale
- An incident where current observability misses the root cause -> proves we need richer metrics
- Cost of Streamlit/Django dashboards exceeds 1 hour/week of maintenance

## When un-deferred, the build

1. Deploy `prom/prometheus` + `grafana/grafana` Docker stack on e5-mother
2. Add `prometheus_client` to every Hive service (already in `litellm` deps)
3. Define SLOs per service (XLM bot uptime, broker pipeline throughput, etc.)
4. Migrate Slack alerts from cron-based to Prometheus alertmanager rules
5. Build 4 Grafana dashboards: System Health, Broker Funnel, XLM Bot, Hive Activity

Estimated effort when un-deferred: 3 working days, $0 incremental cost
(stack runs on existing e5-mother).
