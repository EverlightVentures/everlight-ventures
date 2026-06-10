---
name: canonical_log_line
description: One log entry per request that captures the entire story -- who, what, outcome, timing, DB cost, errors. Beats spelunking through scattered spans.
---

When to use:
- Building any request-handling code path (HTTP endpoint, cron task, Slack handler, MCP tool, agent dispatch).

Pattern (Python, slog/structlog-style):

```python
log = structlog.get_logger()
start = time.monotonic()
db_time, db_calls = 0, 0

# ... do the work, accumulating db_time + db_calls ...

log.info(
    "request",
    correlation_id=ctx.correlation_id,
    actor=ctx.actor_id,
    op=ctx.op_name,
    outcome=outcome,            # "ok" | "error" | "timeout"
    duration_ms=int((time.monotonic() - start) * 1000),
    db_time_ms=db_time,
    db_calls=db_calls,
    artifact_ids=produced,      # list of ids written
    err_type=type(e).__name__ if e else None,
    err_msg=str(e) if e else None,
)
```

Required fields (every canonical line):
- correlation_id, actor, op, outcome, duration_ms, db_time_ms, db_calls, artifact_ids, err_type, err_msg

Why it matters:
- 9/10 incidents are diagnosed from this single entry without crossing service boundaries.
- "Duration suspicious" + "db_time = 90% of duration" tells you exactly where to dig.
- artifact_ids gives you the foreign-key trail to follow into HiveArtifact / Blinko / Supabase.

Anti-pattern:
- Logging at every step inside a request ("checking auth... validating input... writing record...") and nothing at the end. You end up grepping spans + correlating manually. Use canonical line + tracing spans for the journey.
