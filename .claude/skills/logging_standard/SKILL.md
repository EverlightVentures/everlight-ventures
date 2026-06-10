---
name: logging_standard
description: Hive-wide logging discipline. Structured JSON, level hierarchy, correlation IDs, sampling, retention, no-PII guard. From "12 Logging BEST Practices" + "Microservices Logging Standard" transcripts.
---

When to use:
- Writing or reviewing any code that emits log lines (Python, shell, JS).
- Adding a new service to Oracle or phone.

Mandatory shape (8 rules):

1. **Structured JSON, never freeform text.** Each line is a parseable record with `timestamp`, `service`, `env`, `version`, `level`, `correlation_id`, plus message-specific fields. Use Python `structlog` or `slog` equivalent.

2. **4 levels only:** `INFO` (business-as-usual), `WARN` (early warning), `ERROR` (something broke but service alive), `FATAL` (process dying). `DEBUG` is dev-only, never on in prod.

3. **Correlation ID on every request.** Generate at the entry point (HTTP request, cron tick, Slack event, MCP tool call). Pass through every downstream call. Without this, distributed debugging is blind.

4. **Canonical log line per request.** One end-of-request entry summarizing: who, what, outcome, duration_ms, db_time_ms, db_query_count, plus any exception stack. Read 9/10 incidents from this single entry instead of grepping spans.

5. **Sample aggressively.** 20% on success-path INFO. 100% on ERROR/FATAL. Tunable per endpoint when traffic spikes. Cuts cost 80%+ without losing signal.

6. **Retention policy from day one.** Errors 90d, INFO 30d, DEBUG 7d, security/audit 365d. Set BEFORE the first cloud bill. Move >7d logs to cold storage.

7. **Never log secrets.** Redact at the producer level: passwords, full credit card, SSN, full API keys. Use a redaction filter on the logger pipeline (e.g. `resend_guard`-style for Resend keys). The best leak is the one that never enters the logger.

8. **Centralize.** All Hive services log to ONE store (currently Django HiveArtifact + Blinko + jsonl on Oracle). Never SSH into 7 services to grep.

Hive-specific:
- All bot/agent runs MUST go through `content_tools.hive_logger.current_run()` chokepoint.
- All emails through `branded_mailer` (which logs through `resend_guard`).
- All Slack posts through `branded_slack` (which logs to HiveArtifact).
- Logs >7d age go through `memory_pipeline.ingest_before_delete()` before reclamation.

Output contract:
- Every commit touching a log statement also adds the correlation_id field if missing.
- New services ship with retention policy in their systemd unit / cron header.
- Code review catches: freeform text logs, missing correlation_id, log of password/secret pattern.
