"""
Marcus Daily Rollup -- Chief of Staff report-up to Rich.

Rich's instruction (2026-05-17):
  "We have Slack logs. People report to Marcus. So Marcus can tell me,
   hey, this person did this because of this. Using rationale to support
   decision and logics, which is the assigned job duties."

This is that report.

Reads:
  _logs/send_authority_gate.jsonl    -- every gate decision (pass + fail)
  _logs/branded_mailer_audit.jsonl   -- every gated send
  _logs/resend_budget.jsonl          -- every Resend POST
  _logs/inbound/real_replies.jsonl   -- matched real-reply inbound
  _logs/inbound/hot_inbound.jsonl    -- total inbound (for promo-vs-real ratio)

Renders:
  Plain-English daily summary in Marcus's voice. Numbers + rationale.

Publishes via canonical 3-format pipeline:
  publish_gdoc() -> HTML on e5-mother + Google Doc + branded Slack card
                     with "View full report" button to #ceo-brief.

CLI:
  python marcus_daily_rollup.py              # today's rollup
  python marcus_daily_rollup.py --date 2026-05-17
  python marcus_daily_rollup.py --dry-run    # build but don't publish
  python marcus_daily_rollup.py --since 24h  # last N hours instead of calendar day
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

_WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
_LOG_DIR = _WORKSPACE / "_logs"
_CT_DIR = _WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
if str(_CT_DIR) not in sys.path:
    sys.path.insert(0, str(_CT_DIR))

log = logging.getLogger("marcus_daily_rollup")


# ----------------------------------------------------------------------------
# Time window
# ----------------------------------------------------------------------------
PT_OFFSET = timedelta(hours=-7)  # PDT in May 2026


def parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def window_pt_day(date_str: str) -> tuple[datetime, datetime]:
    """Given YYYY-MM-DD, return UTC bounds for that Pacific calendar day."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    start_pt = d.replace(tzinfo=timezone(PT_OFFSET))
    end_pt = start_pt + timedelta(days=1)
    return start_pt.astimezone(timezone.utc), end_pt.astimezone(timezone.utc)


def window_since(hours: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    return start, end


# ----------------------------------------------------------------------------
# Log readers
# ----------------------------------------------------------------------------
def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue


def in_window(row: dict[str, Any], start: datetime, end: datetime, ts_field: str = "ts_utc") -> bool:
    ts = parse_ts(row.get(ts_field, "") or row.get("ts", ""))
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return start <= ts < end


# ----------------------------------------------------------------------------
# Pull + aggregate
# ----------------------------------------------------------------------------
def collect(start: datetime, end: datetime) -> dict[str, Any]:
    """Pull all log rows that fall in the window. Return aggregates."""
    gate_rows = [r for r in iter_jsonl(_LOG_DIR / "send_authority_gate.jsonl") if in_window(r, start, end)]
    mailer_rows = [r for r in iter_jsonl(_LOG_DIR / "branded_mailer_audit.jsonl") if in_window(r, start, end, "ts") or in_window(r, start, end, "ts_utc")]
    budget_rows = [r for r in iter_jsonl(_LOG_DIR / "resend_budget.jsonl") if in_window(r, start, end, "ts")]
    reply_rows = [r for r in iter_jsonl(_LOG_DIR / "inbound" / "real_replies.jsonl") if in_window(r, start, end, "matcher_ts_utc") or in_window(r, start, end, "ts_utc")]
    inbound_rows = [r for r in iter_jsonl(_LOG_DIR / "inbound" / "hot_inbound.jsonl") if in_window(r, start, end, "ts_utc")]

    # Gate verdicts
    verdicts = Counter(r.get("verdict", "?") for r in gate_rows)
    blocked_rows = [r for r in gate_rows if r.get("verdict", "").startswith("blocked")]
    overrides = [r for r in gate_rows if r.get("verdict", "").startswith("override")]
    authorized = [r for r in gate_rows if r.get("verdict") == "authorized"]

    # Per-persona breakdown
    per_persona_attempts = defaultdict(lambda: {"authorized": 0, "blocked": 0, "blocked_reasons": []})
    for r in gate_rows:
        p = r.get("persona_id", "unknown")
        if r.get("verdict") == "authorized":
            per_persona_attempts[p]["authorized"] += 1
        elif r.get("verdict", "").startswith("blocked"):
            per_persona_attempts[p]["blocked"] += 1
            per_persona_attempts[p]["blocked_reasons"].append(r.get("verdict"))

    # Sends through canonical pipeline
    sends_canonical = len(mailer_rows)
    sends_resend_seen = len(budget_rows)
    sends_outside_pipeline = max(0, sends_resend_seen - sends_canonical)

    # Inbound classification
    inbound_total = len(inbound_rows)
    real_replies = len(reply_rows)
    promo_or_unmatched = inbound_total - real_replies

    return {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "gate": {
            "total": len(gate_rows),
            "verdicts": dict(verdicts),
            "blocked_count": len(blocked_rows),
            "override_count": len(overrides),
            "authorized_count": len(authorized),
            "blocked_rows": blocked_rows[:20],
            "override_rows": overrides[:20],
        },
        "sends": {
            "canonical": sends_canonical,
            "resend_seen": sends_resend_seen,
            "outside_pipeline": sends_outside_pipeline,
            "rows": mailer_rows[:20],
        },
        "inbound": {
            "total": inbound_total,
            "real_replies": real_replies,
            "promo_or_unmatched": promo_or_unmatched,
            "reply_rows": reply_rows[:20],
        },
        "per_persona": dict(per_persona_attempts),
    }


# ----------------------------------------------------------------------------
# Render -- Marcus's voice, plain English, numbers + rationale.
# ----------------------------------------------------------------------------
def render(agg: dict[str, Any], date_label: str) -> tuple[str, str]:
    """Return (title, markdown_body) tuple."""
    g = agg["gate"]
    s = agg["sends"]
    i = agg["inbound"]

    # Headline
    if s["canonical"] == 0 and i["real_replies"] == 0 and g["blocked_count"] == 0:
        headline_status = "🟡 QUIET DAY"
        headline = "No outbound, no replies, no blocked attempts. Pipeline idle."
    elif g["blocked_count"] > 0 or s["outside_pipeline"] > 0:
        headline_status = "🔴 ATTENTION"
        headline = f"{g['blocked_count']} gate blocks. {s['outside_pipeline']} sends outside canonical pipeline."
    else:
        headline_status = "🟢 NOMINAL"
        headline = f"{s['canonical']} sends shipped, {i['real_replies']} real replies routed."

    title = f"Marcus Daily Rollup -- {date_label}"

    body = []
    body.append(f"## {headline_status}")
    body.append(f"_{headline}_\n")

    # Pipeline activity
    body.append("## Pipeline Activity\n")
    body.append(f"- **Sends through canonical pipeline:** {s['canonical']}")
    body.append(f"- **Total Resend API hits seen:** {s['resend_seen']}")
    if s["outside_pipeline"] > 0:
        body.append(f"- ⚠️  **Sends OUTSIDE canonical pipeline:** {s['outside_pipeline']}  -- investigate immediately, this means a script bypassed branded_mailer")
    body.append(f"- **Authority gate decisions:** {g['total']}  ({g['authorized_count']} authorized, {g['blocked_count']} blocked, {g['override_count']} operator override)")
    body.append("")

    # Blocked attempts -- the "Marcus tells me why"
    if g["blocked_rows"]:
        body.append("## Blocked Send Attempts (with rationale)\n")
        for r in g["blocked_rows"]:
            ts = (r.get("ts_utc") or "")[:19].replace("T", " ")
            persona = r.get("persona_id", "?")
            to = r.get("to", "?")
            state = r.get("state", "-")
            verdict = r.get("verdict", "?")
            caller = r.get("caller", "?")
            reason = {
                "blocked_back_office_hardcoded": "back-office persona attempted to email a counterparty (Constitutional violation)",
                "blocked_back_office_yaml": "back-office persona per yaml policy",
                "blocked_not_live": f"persona is STAGING (promote_blocker: {str(r.get('promote_blocker','-'))[:120]})",
                "blocked_wrong_territory": f"persona territory is {r.get('allowed','?')}, recipient is {state}",
                "blocked_unknown_persona": "persona not registered in senders_authority.yaml",
            }.get(verdict, verdict)
            body.append(f"- `{ts}` -- **{persona}** -> {to} ({state})")
            body.append(f"    - **Why blocked:** {reason}")
            body.append(f"    - **Caller script:** `{caller}`")
        body.append("")

    # Operator overrides
    if g["override_rows"]:
        body.append("## Operator Overrides Fired\n")
        for r in g["override_rows"]:
            ts = (r.get("ts_utc") or "")[:19].replace("T", " ")
            body.append(f"- `{ts}` -- **{r.get('persona_id','?')}** -> {r.get('to','?')} ({r.get('state','-')}) by `{r.get('caller','?')}`")
        body.append("")

    # Successful sends
    if s["rows"]:
        body.append("## Successful Sends Today\n")
        for r in s["rows"]:
            ts = (r.get("ts") or r.get("ts_utc") or "")[:19].replace("T", " ")
            body.append(f"- `{ts}` -- {r.get('to','?')} -- _{r.get('subject','(no subject)')[:80]}_")
        body.append("")

    # Real replies routed
    if i["reply_rows"]:
        body.append("## Real Replies Routed to Agents\n")
        for r in i["reply_rows"]:
            ts = (r.get("ts_utc") or "")[:19].replace("T", " ")
            mo = r.get("matched_outbound", {})
            body.append(f"- `{ts}` -- **{r.get('from_email','?')}** replied to **{mo.get('persona_id','?')}**")
            body.append(f"    - Original subject: _{mo.get('original_subject','-')[:80]}_")
            body.append(f"    - Routed to: `_state/agent_inboxes/{mo.get('persona_id','unrouted')}/`")
        body.append("")

    # Inbound noise summary
    body.append("## Inbound Noise Summary\n")
    body.append(f"- **Total inbound rows seen:** {i['total']}")
    body.append(f"- **Real replies (matched outbound):** {i['real_replies']}")
    body.append(f"- **Promo / unmatched:** {i['promo_or_unmatched']}")
    if i["total"] > 0:
        signal_ratio = (i["real_replies"] / i["total"]) * 100
        body.append(f"- **Signal ratio:** {signal_ratio:.1f}%  (real replies / total inbound)")
    body.append("")

    # Per-persona attempts
    if agg["per_persona"]:
        body.append("## Per-Persona Attempts\n")
        body.append("| Persona | Authorized | Blocked |")
        body.append("|---|---:|---:|")
        for p, counts in sorted(agg["per_persona"].items()):
            body.append(f"| `{p}` | {counts['authorized']} | {counts['blocked']} |")
        body.append("")

    # Footer
    body.append("---")
    body.append("_Marcus Cole, Chief of Staff -- Everlight Ventures._  ")
    body.append(f"_Window: {agg['window_start'][:16]} -> {agg['window_end'][:16]} (UTC)._  ")
    body.append("_5-layer defense: WHOLESALE_OUTBOUND_HALT, eradication_gate, send_authority_gate, DNC, resend_budget._")

    return title, "\n".join(body)


def summary_line(agg: dict[str, Any]) -> str:
    g = agg["gate"]
    s = agg["sends"]
    i = agg["inbound"]
    bits = []
    bits.append(f"{s['canonical']} sends")
    bits.append(f"{i['real_replies']} replies")
    bits.append(f"{g['blocked_count']} blocked")
    if s["outside_pipeline"] > 0:
        bits.append(f"⚠️ {s['outside_pipeline']} OUTSIDE pipeline")
    return " | ".join(bits)


# ----------------------------------------------------------------------------
# Publish
# ----------------------------------------------------------------------------
def publish(title: str, body: str, summary: str, channel: str = "#ceo-brief") -> dict:
    try:
        from n8n_replacements import publish_gdoc
    except ImportError as e:
        return {"ok": False, "error": f"publish_gdoc unavailable: {e}"}
    return publish_gdoc(
        title=title,
        body=body,
        channel=channel,
        folder_key="ai_hive",
        summary=summary,
        extra_meta={
            "Agent": "Marcus Cole, Chief of Staff",
            "Generated by": "marcus_daily_rollup.py",
            "Defense stack": "5-layer (halt + eradication + authority + DNC + budget)",
        },
    )


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    p = argparse.ArgumentParser(description="Marcus Daily Rollup")
    p.add_argument("--date", help="YYYY-MM-DD (Pacific). Default: today PT")
    p.add_argument("--since", help="last N hours (e.g. '24h'). Overrides --date.")
    p.add_argument("--channel", default="#ceo-brief", help="Slack channel for the announcement")
    p.add_argument("--dry-run", action="store_true", help="render but do not publish")
    args = p.parse_args()

    if args.since:
        hours = int(args.since.rstrip("h"))
        start, end = window_since(hours)
        date_label = f"last {hours}h"
    else:
        date_str = args.date or (datetime.now(timezone(PT_OFFSET)) - timedelta(hours=0)).strftime("%Y-%m-%d")
        start, end = window_pt_day(date_str)
        date_label = f"{date_str} (Pacific)"

    agg = collect(start, end)
    title, body = render(agg, date_label)
    summary = summary_line(agg)

    print("=" * 70)
    print(title)
    print("=" * 70)
    print(summary)
    print("-" * 70)
    print(body)
    print("=" * 70)

    if args.dry_run:
        print("\n[DRY-RUN] not publishing")
        sys.exit(0)

    res = publish(title=title, body=body, summary=summary, channel=args.channel)
    print("\nPublish result:")
    print(json.dumps(res, indent=2, default=str))
